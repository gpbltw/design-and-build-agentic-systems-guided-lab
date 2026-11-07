import argparse
import asyncio
import json
import os
from typing import Any, Dict, List
import uuid
import importlib

from dotenv import load_dotenv
from pathlib import Path

load_dotenv(Path(__file__).resolve().parents[2] / ".env", override=True)

# ==========================================
# ПАТЧ ДЛЯ GROQ (работает при любом запуске)
# ==========================================
import openai
from openai import AsyncOpenAI
from agents import (
    set_default_openai_client, 
    set_default_openai_api, 
    set_tracing_disabled, 
    OpenAIChatCompletionsModel, 
    Agent
)

# 1. Настраиваем глобальный клиент Groq
set_tracing_disabled(True)
groq_client = AsyncOpenAI(
    base_url="https://api.groq.com/openai/v1", 
    api_key=os.getenv("OPENAI_API_KEY")
)
set_default_openai_client(groq_client)
set_default_openai_api("chat_completions")

# 2. Принудительно переводим всех агентов на OpenAIChatCompletionsModel
_orig_agent_init = Agent.__init__
def _patched_agent_init(self, *args, **kwargs):
    if "model" in kwargs and isinstance(kwargs["model"], str):
        kwargs["model"] = OpenAIChatCompletionsModel(
            model=kwargs["model"],
            openai_client=groq_client
        )
    _orig_agent_init(self, *args, **kwargs)
Agent.__init__ = _patched_agent_init

# 3. ФИНАЛЬНЫЙ ПАТЧ ЗАПРОСА (вставляем dummy и добавляем его в required)
_orig_create = openai.resources.chat.completions.AsyncCompletions.create
async def _patched_create(self, *args, **kwargs):
    kwargs.pop("verbosity", None)
    kwargs.pop("reasoning_effort", None)
    
    if "tools" in kwargs and kwargs["tools"]:
        tools_list = json.loads(json.dumps(
            kwargs["tools"], 
            default=lambda o: o.model_dump() if hasattr(o, "model_dump") else str(o)
        ))
        
        def fix_schemas(schema):
            if isinstance(schema, dict):
                if schema.get("type") == "object":
                    # Если properties пустой или его нет - добавляем dummy
                    if "properties" not in schema or not schema["properties"]:
                        schema["properties"] = {
                            "dummy": {
                                "type": "string",
                                "description": "Ignore this argument."
                            }
                        }
                    
                    # Groq требует, чтобы ВСЕ свойства были в required
                    if "properties" in schema and schema["properties"]:
                        if "required" not in schema:
                            schema["required"] = []
                        for prop in schema["properties"]:
                            if prop not in schema["required"]:
                                schema["required"].append(prop)

                for val in schema.values():
                    fix_schemas(val)
            elif isinstance(schema, list):
                for item in schema:
                    fix_schemas(item)
                    
        fix_schemas(tools_list)
        kwargs["tools"] = tools_list

    return await _orig_create(self, *args, **kwargs)

openai.resources.chat.completions.AsyncCompletions.create = _patched_create
# ==========================================

from agents import Runner
from agents.exceptions import InputGuardrailTripwireTriggered
from agents.run import RunConfig
from agents.items import (
    MessageOutputItem, ToolCallItem, ToolCallOutputItem,
    HandoffCallItem, HandoffOutputItem, ItemHelpers
)

def write_agent_model_answers(records: List[Dict[str, Any]], output_path: str) -> None:
    parent_dir = os.path.dirname(os.path.abspath(output_path))
    if parent_dir and not os.path.exists(parent_dir):
        os.makedirs(parent_dir, exist_ok=True)

    def extract_model_toolcall(rec: Dict[str, Any]) -> str:
        if "model_toolcall" in rec and rec["model_toolcall"]:
            return rec["model_toolcall"]
        toolcall_sequence = []
        trace = rec.get("trace") or rec.get("steps") or []
        if isinstance(trace, str):
            try: trace = json.loads(trace)
            except Exception: trace = []
        if isinstance(trace, list):
            for step in trace:
                tool_name = step.get("tool_name") or step.get("tool")
                if tool_name: toolcall_sequence.append(str(tool_name))
                handoff_name = step.get("handoff_to") or step.get("handoff")
                if handoff_name: toolcall_sequence.append(f"handoff:{handoff_name}")
        return " -> ".join(toolcall_sequence) if toolcall_sequence else "none"

    with open(output_path, "w", encoding="utf-8") as f:
        for rec in records:
            item = {
                "input": rec.get("input", ""),
                "expected_answer": rec.get("expected_answer"),
                "expected_tool": rec.get("expected_tool"),
                "expected_category": rec.get("expected_category"),
                "model_answer": rec.get("model_answer", ""),
                "model_toolcall": extract_model_toolcall(rec),
            }
            f.write(json.dumps({"item": item}, ensure_ascii=False) + "\n")

def _load_router_module(use_solution: bool):
    module_name = ".router_solution" if use_solution else ".router"
    return importlib.import_module(module_name, package=__package__)

def load_tests(path: str) -> List[Dict[str, Any]]:
    out = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line: continue
            try:
                data = json.loads(line)
                item = data.get("item", {})
                if isinstance(item, dict):
                    out.append({
                        "user": item.get("input", ""),
                        "expected_tool": item.get("expected_tool"),
                        "expected_answer": item.get("expected_answer"),
                        "expected_category": item.get("expected_category"),
                    })
            except Exception:
                continue
    return out

def build_agent_for_variant(variant: str, routers_module):
    if variant.upper() == "TRIAGE":
        return routers_module.build_triage_routed_agents()
    if variant.upper() == "AGENT_AS_TOOL":
        return routers_module.build_handoff_tool_pattern()
    if variant.upper() in ("GUARDRAIL"):
        return routers_module.build_guardrailed_triage_agent_with_guardrails()
    raise ValueError("Unknown variant")

async def run_suite(variant: str, tests_path: str, routers_module) -> None:
    agent = build_agent_for_variant(variant, routers_module)
    tests = load_tests(tests_path)

    workflow_name = f"Agents Challenge Variant {variant}"
    group_id = str(uuid.uuid4())
    run_config = RunConfig(workflow_name=workflow_name, group_id=group_id)

    print(f"\n Find Agent Traces for workflow_name: {workflow_name} with Group ID: {group_id} at https://platform.openai.com/logs/trace")

    jsonl_records = []

    for idx, t in enumerate(tests, start=1):
        user = t.get("user", "")
        print("\n" + "-" * 40)
        print(f"Example {idx}")
        print(f"User > {user}")

        model_answer_text = ""
        toolcall_parts = []

        try:
            result = await Runner.run(agent, user, max_turns=4, run_config=run_config)
            for item in getattr(result, "new_items", []):
                agent_name = getattr(item.agent, "name", "Agent") if hasattr(item, "agent") else "Agent"
                if isinstance(item, MessageOutputItem):
                    text = ItemHelpers.text_message_output(item) or ""
                    print(f"[OUTPUT] {agent_name} > {text}")
                    if text: model_answer_text = text
                elif isinstance(item, ToolCallItem):
                    name = getattr(getattr(item, "raw_item", None), "name", "tool")
                    args = getattr(getattr(item, "raw_item", None), "arguments", None)
                    print(f"[TOOLCALL] {agent_name} > {name} args={args}")
                    if name: toolcall_parts.append(str(name))
                elif isinstance(item, ToolCallOutputItem):
                    print(f"[TOOL RESULT] > {item.output}")
                elif isinstance(item, HandoffCallItem):
                    target = getattr(getattr(item, "raw_item", None), "name", "handoff")
                    print(f"[HANDOFF REQUEST] {agent_name} is requesting to hand off to agent: {target}")
                    if target: toolcall_parts.append(f"handoff:{target}")
                elif isinstance(item, HandoffOutputItem):
                    src = item.source_agent.name if getattr(item, "source_agent", None) else "Unknown"
                    dst = item.target_agent.name if getattr(item, "target_agent", None) else "Unknown"
                    print(f"[HANDOFF COMPLETE] Conversation control transferred from {src} to {dst}")

        except InputGuardrailTripwireTriggered:
            print("[GUARDRAIL]- TRIPWIRE TRIGGERED")
            model_answer_text = "[GUARDRAIL] Tripwire triggered"
            toolcall_parts.append("guardrail_tripwire")
        except Exception as e:
            print(f"Error > {e}")
            model_answer_text = f"[ERROR] {e}"
            toolcall_parts.append("error")

        jsonl_records.append({
            "input": user,
            "expected_tool": t.get("expected_tool"),
            "expected_answer": t.get("expected_answer"),
            "expected_category": t.get("expected_category"),
            "model_answer": model_answer_text,
            "model_toolcall": " -> ".join(toolcall_parts) if toolcall_parts else "none",
        })

    default_output_path = os.path.normpath(os.path.join(os.path.dirname(__file__), "../data/agent_model_answer.jsonl"))
    write_agent_model_answers(jsonl_records, default_output_path)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--variant", required=True)
    parser.add_argument("--solution", action="store_true")
    args = parser.parse_args()
    default_tests_path = os.path.join(os.path.dirname(__file__), "../data/sample_02.jsonl")
    routers_module = _load_router_module(use_solution=args.solution)
    asyncio.run(run_suite(args.variant, tests_path=default_tests_path, routers_module=routers_module))

if __name__ == "__main__":
    main()