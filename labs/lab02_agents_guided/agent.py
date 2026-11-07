import asyncio
import os
import openai
import copy

# Load environment variables from a local `.env` (if present) so the Agents SDK
# can pick up OPENAI_API_KEY without manual exports.
from dotenv import load_dotenv
from pathlib import Path

load_dotenv(Path(__file__).resolve().parents[2] / ".env", override=True)

from openai import AsyncOpenAI
from agents import Agent, Runner, set_tracing_disabled, set_default_openai_client, set_default_openai_api, OpenAIChatCompletionsModel
from .tools import (
    lookup_order, raise_complaint, check_payment_methods, 
    cancel_order, FAQ_retrieval
)

# ==========================================
# ПАТЧ ДЛЯ GROQ (вырезаем OpenAI-параметры)
# ==========================================
_original_create = openai.resources.chat.completions.AsyncCompletions.create
async def _patched_create(self, *args, **kwargs):
    kwargs.pop("verbosity", None)
    kwargs.pop("reasoning_effort", None)
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

# ==========================================
# НАСТРОЙКА GROQ
# ==========================================
set_tracing_disabled(True)
groq_client = AsyncOpenAI(
    base_url="https://api.groq.com/openai/v1", 
    api_key=os.getenv("OPENAI_API_KEY")
)
set_default_openai_client(groq_client)
set_default_openai_api("chat_completions")

# ==========================================
# ЛОГИКА АГЕНТА
# ==========================================
NAME = "Baseline Support Agent"

BASELINE_SYSTEM_PROMPT = """\
You are a customer-support assistant for order-related requests.

You have access to the following tools:
- lookup_order: Look up details for a specific order by its order number.
- complaint: Start a complaint intake process for the customer.
- check_payment_methods: List the accepted payment methods.
- FAQ_retrieval: Look up an FAQ question and answer pair.

Guidelines:
- Always ask for any missing required information (such as Order Number) before calling a tool.
- Call exactly one tool at a time.
- Keep your answers concise and user-friendly.
- Never list the tools you have access to in your response.
"""

def build_baseline_agent() -> Agent:
    # Явно оборачиваем модель, чтобы SDK не отрезал префикс "openai/"
    groq_model = OpenAIChatCompletionsModel(
        model="openai/gpt-oss-20b",
        openai_client=groq_client
    )
    
    agent = Agent(
        name=NAME,
        instructions=BASELINE_SYSTEM_PROMPT,
        tools=[lookup_order, raise_complaint, check_payment_methods, cancel_order, FAQ_retrieval],
        model=groq_model,
    )
    return agent

async def run_once(agent: Agent, user_input: str) -> str:
    result = await Runner.run(agent, user_input)
    return str(result.final_output)

if __name__ == "__main__":
    async def _main():
        questions = [
            "What are your customer service hours?",
            "I need to raise a complaint, as I am not happy with my order.",
            "I need to understand my order status, the order number is 123-456.",
            "I need to understand my order status, the order number is A123-456.",
            "I need to cancel my order, the order number is A123-456.",
            "What is the status of my order, the order number is A123-456.",
            "I need to know how to pay for my order.",
        ]
        agent = build_baseline_agent()
        for question in questions:
            print("-" * 40)
            print(f"User > {question}")
            try:
                out = await run_once(agent, question)
                print("Agent >", out)
            except Exception as e:
                print(f"Error > {e}")

    asyncio.run(_main())