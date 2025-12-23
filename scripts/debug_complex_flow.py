#!/usr/bin/env python
"""Debug script for complex banking scenario: Digression + Resume + Correction."""

import asyncio
import importlib
import logging

import dspy
from langgraph.checkpoint.memory import MemorySaver

from soni.config.loader import ConfigLoader
from soni.runtime.loop import RuntimeLoop

# Enable logging
logging.basicConfig(level=logging.INFO, format="%(name)s - %(levelname)s - %(message)s")
# Optional: Set specific loggers to DEBUG to see transitions
# logging.getLogger("soni.dm.nodes.understand").setLevel(logging.DEBUG)
# logging.getLogger("soni.dm.nodes.execute_flow").setLevel(logging.DEBUG)

# Load banking handlers
importlib.import_module("examples.banking.handlers")


async def main():
    print("=" * 70)
    print("COMPLEX FLOW DEBUG - Digression + Resume + Correction")
    print("=" * 70)

    # Load banking config
    config = ConfigLoader.load("examples/banking/domain")

    # Setup DSPy (using mini for speed and cost)
    dspy.configure(lm=dspy.LM("openai/gpt-4o-mini"))

    # Create runtime with memory checkpointer
    checkpointer = MemorySaver()
    async with RuntimeLoop(config=config, checkpointer=checkpointer) as runtime:
        user_id = "complex_debug_user"

        print("\n--- Step 1: Start transfer (100€ to mom) ---")
        response = await runtime.process_message("I want to transfer 100€ to my mom", user_id)
        print(f"Bot: {response}")

        print("\n--- Step 2: Digression (check balance) ---")
        response = await runtime.process_message("wait, how much money do I have?", user_id)
        print(f"Bot: {response}")

        print("\n--- Step 3: Complete digression (checking) ---")
        # This completes check_balance and should resume transfer_funds
        response = await runtime.process_message("checking", user_id)
        print(f"Bot: {response}")

        print("\n--- Step 4: Resume transfer (provide IBAN) ---")
        response = await runtime.process_message("ES9121000418450200051332", user_id)
        print(f"Bot: {response}")

        print("\n--- Step 5: Provide Concept ---")
        response = await runtime.process_message("birthday gift", user_id)
        print(f"Bot: {response}")

        print("\n--- Step 6: Provide Source Account ---")
        response = await runtime.process_message("checking", user_id)
        print(f"Bot: {response}")

        print("\n--- Step 7: Correction during Confirmation (change to 200€) ---")
        # The Confirmation step should catch this correction intent
        response = await runtime.process_message("no, change it to 200€", user_id)
        print(f"Bot: {response}")

        print("\n--- Step 8: Final Confirmation ---")
        response = await runtime.process_message("yes", user_id)
        print(f"Bot: {response}")

        print("\n" + "=" * 70)
        # Verification of final result
        if "200" in response or "processed" in response.lower():
            print("✓ SUCCESS: Complex flow completed with correction!")
        else:
            print(f"✗ FAILED: Expected confirmation of 200€ or processed message. Got: {response}")
        print("=" * 70)


if __name__ == "__main__":
    asyncio.run(main())
