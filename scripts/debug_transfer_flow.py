import asyncio
import logging
import sys
from typing import Any

import dspy
from langgraph.checkpoint.memory import MemorySaver

# Make sure we can import soni
sys.path.append(".")

import examples.banking.handlers  # Register actions
from soni.config import SoniConfig
from soni.runtime.loop import RuntimeLoop

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configure DSPy
dspy.configure(lm=dspy.LM("openai/gpt-4o-mini"))


async def debug_flow():
    """Debug the transfer flow specifically checking slot persistence."""
    print("\n--- Starting Debug Session ---\n")

    # 1. Load Banking Config
    try:
        config = SoniConfig.from_yaml("examples/banking/domain")
    except Exception as e:
        print(f"Error loading config: {e}")
        return

    # 2. Initialize Runtime
    checkpointer = MemorySaver()
    runtime = RuntimeLoop(config, checkpointer=checkpointer)
    await runtime.initialize()

    user_id = "debug_user_001"

    # Helper to print slots
    async def print_slots(tag: str):
        state = await runtime.get_state(user_id)
        slots = state.get("flow_slots", {}) if state else {}
        print(f"[{tag}] Current Slots: {slots}")
        return state

    # --- Turn 1: Init Transfer ---
    print("\n>>> Turn 1: 'I want to transfer money to my mom'")
    response1 = await runtime.process_message("I want to transfer money to my mom", user_id)
    print(f"Bot: {response1}")
    await print_slots("After Turn 1")

    # --- Turn 2: Provide IBAN ---
    print("\n>>> Turn 2: '245252' (IBAN)")
    response2 = await runtime.process_message("245252", user_id)
    print(f"Bot: {response2}")

    state = await print_slots("After Turn 2")

    # Turn 3: 100 EUR
    print("\n>>> Turn 3: '100' (Amount)")
    response3 = await runtime.process_message("100", user_id)
    print(f"Bot: {response3}")
    await print_slots("After Turn 3")

    print("\n--- Debug Session Complete ---")


if __name__ == "__main__":
    asyncio.run(debug_flow())
