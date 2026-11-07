import asyncio

# Load environment variables from a local `.env` (if present) so the Agents SDK
# can pick up OPENAI_API_KEY without manual exports.
from dotenv import load_dotenv
from pathlib import Path

load_dotenv(Path(__file__).resolve().parents[2] / ".env", override=True)

from agents import Agent, Runner, SQLiteSession
from .tools_solution import lookup_order, raise_complaint, check_payment_methods, cancel_order, FAQ_retrieval

#Step 6: Enable multi-turn memory using the SQLiteSession
NAME = "Baseline Support Agent"
session = SQLiteSession(NAME)

#Step 1: Refine the system prompt
BASELINE_SYSTEM_PROMPT = """\
You are a customer-support assistant for order-related requests.

You have access to the following tools:
- lookup_order: Look up details for a specific order by its order number.
- complaint: Start a complaint intake process for the customer.
- contact_customer_service: Provide customer service contact information.
- check_payment_methods: List the accepted payment methods.
- FAQ_retrieval: Look up an FAQ question and answer pair.

Guidelines:
- Always ask for any missing required information (such as Order Number) before calling a tool.
- Call exactly one tool at a time.
- Keep your answers concise and user-friendly.
- Never list the tools you have access to in your response.
"""

#Step 2: Implement tools functions in tools.py
#Step 3: Implement the `build_baseline_agent()` function to construct the agent with the several tools.
def build_baseline_agent() -> Agent:
    """
    Construct the baseline single agent with several tools registered.
    """
    agent = Agent(
        name=NAME,
        instructions=BASELINE_SYSTEM_PROMPT,
        tools=[lookup_order, raise_complaint, check_payment_methods, cancel_order, FAQ_retrieval],
        model="openai/gpt-oss-20b",
        # Optional: model_config can be set here if you wish to override defaults.
        # model_config=...
    )
    return agent


async def run_once(agent: Agent, user_input: str, session: SQLiteSession) -> str:
    """
    Run a single-turn agent interaction and return the final output string.
    """
    result = await Runner.run(agent, user_input, session=session)
    # result.final_output is str unless you define an output_type.
    return str(result.final_output)

#Step 4: Test the agent with several examples, testing different tools and validating the agent's behavior and response.
#Step 5: implement cancel_order tool in tools.py and add it to the build_baseline_agent() function
#Step 6: Enable multi-turn memory using the SQLiteSession
if __name__ == "__main__":
    async def _main():
        # Example test harness for the agent using the run_once function.
        # This demonstrates how to interact with the agent for five different user queries.

        questions = [
            "What are your customer service hours?",
            "I need to raise a complaint, as I am not happy with my order.",
            "I need to understand my order status, the order number is 123-456.",
            "I need to understand my order status, the order number is A123-456.",
            "I need to cancel my order, the order number is A123-456.",
            "What is the status of my order, the order number is A123-456.",
            "I need to know how to pay for my order.",
        ]

        # Build the agent instance
        agent = build_baseline_agent()

        for question in questions:
            out = await run_once(agent, question, session)
            print("-" * 40)
            print(f"User > {question}")
            print("Agent >", out)

    asyncio.run(_main())
