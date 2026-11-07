import asyncio
import os
import openai
import copy
from openai import AsyncOpenAI
from agents import set_tracing_disabled, OpenAIChatCompletionsModel
from labs.lab02_agents_guided.agent import build_baseline_agent, run_once

# 1. Патч для запросов
_original_create = openai.resources.chat.completions.AsyncCompletions.create
async def _patched_create(self, *args, **kwargs):
    # Удаляем все OpenAI-специфичные параметры, которые ломают Groq
    kwargs.pop("verbosity", None)
    kwargs.pop("reasoning_effort", None) # <--- ДОБАВИЛИ ЭТУ СТРОКУ
    
    if "tools" in kwargs and kwargs["tools"]:
        new_tools = []
        for tool in kwargs["tools"]:
            if hasattr(tool, "model_dump"):
                tool_dict = tool.model_dump()
            elif hasattr(tool, "dict") and not isinstance(tool, dict):
                tool_dict = tool.dict()
            else:
                tool_dict = copy.deepcopy(tool)

            if isinstance(tool_dict, dict) and "function" in tool_dict:
                params = tool_dict["function"].get("parameters", {})
                if not isinstance(params.get("properties"), dict):
                    params["properties"] = {}
                tool_dict["function"]["parameters"] = params
            
            new_tools.append(tool_dict)
        kwargs["tools"] = new_tools
    return await _original_create(self, *args, **kwargs)

openai.resources.chat.completions.AsyncCompletions.create = _patched_create

# 2. Настройка Groq
set_tracing_disabled(True)
groq_client = AsyncOpenAI(base_url="https://api.groq.com/openai/v1", api_key=os.getenv("OPENAI_API_KEY"))
groq_model = OpenAIChatCompletionsModel(model="openai/gpt-oss-20b", openai_client=groq_client)

def ok(label, cond):
    print(("PASS " if cond else "FAIL ") + label)

async def main():
    agent = build_baseline_agent()
    agent.model = groq_model
    
    expected = {'lookup_order','cancel_order','raise_complaint','check_payment_methods','FAQ_retrieval'}
    found = {getattr(t,'name',getattr(t,'__name__',str(t))) for t in agent.tools}
    ok("Tools registered", found == expected)
    
    print("\nRun test 1 (Payment)...")
    out1 = await run_once(agent, "What payment methods do you accept?")
    print("Q1 >", (out1 or "").strip().replace('\n',' ')[:160])
    ok("Run returns output (Q1)", bool(out1 and out1.strip()))

    print("\nRun test 2 (Order)...")
    out2 = await run_once(agent, "I need my order status, my order number is A123-456.")
    print("Q2 >", (out2 or "").strip().replace('\n',' ')[:160])
    ok("Run returns output (Q2)", bool(out2 and out2.strip()))

if __name__ == "__main__":
    asyncio.run(main())