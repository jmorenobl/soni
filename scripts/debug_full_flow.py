#!/usr/bin/env python
"""Debug script that runs the full LangGraph flow to diagnose interrupt/resume."""

import asyncio
import importlib
import logging

import dspy
from langgraph.checkpoint.memory import MemorySaver

from soni.config.loader import ConfigLoader
from soni.dm.builder import build_orchestrator
from soni.runtime.loop import RuntimeLoop

# Enable debug logging
logging.basicConfig(level=logging.INFO, format="%(name)s - %(levelname)s - %(message)s")
# Enable our debug logs specifically
logging.getLogger("soni.compiler.nodes.collect").setLevel(logging.DEBUG)

# Load banking handlers
importlib.import_module("examples.banking.handlers")


async def main():
    print("=" * 70)
    print("FULL FLOW DEBUG - Simulating the exact conversation")
    print("=" * 70)

    # Load config
    config = ConfigLoader.load("examples/banking/domain")

    # Setup DSPy
    dspy.configure(lm=dspy.LM("openai/gpt-4o-mini"))

    # Create runtime with memory checkpointer
    # Create runtime with memory checkpointer
    checkpointer = MemorySaver()
    async with RuntimeLoop(config=config, checkpointer=checkpointer) as runtime:
        user_id = "debug_user"

        # Conversation flow:
        print("\n--- Message 1: Start transfer flow ---")
        response1 = await runtime.process_message("I want to transfer money to my mom", user_id)
        print(f"Bot: {response1}")

        print("\n--- Message 2: Provide IBAN ---")
        response2 = await runtime.process_message("353454", user_id)
        print(f"Bot: {response2}")

        print("\n--- Message 3: Ask about balance (should trigger check_balance flow) ---")
        response3 = await runtime.process_message("how much do I have?", user_id)
        print(f"Bot: {response3}")

        print("\n" + "=" * 70)
        if "balance" in response3.lower() or "check" in response3.lower():
            print("✓ SUCCESS: Digression to check_balance was handled!")
        elif "didn't understand" in response3.lower():
            print("✗ BUG CONFIRMED: Got 'I didn't understand' instead of handling digression")
        else:
            print(f"? UNKNOWN: Response was '{response3}'")
        print("=" * 70)


if __name__ == "__main__":
    asyncio.run(main())
