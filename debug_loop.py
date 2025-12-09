#!/usr/bin/env python3
"""Debug script to trace the infinite loop."""

import asyncio
import logging
import os
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass

import dspy

from soni.runtime import RuntimeLoop

# Enable ALL logging
logging.basicConfig(
    level=logging.DEBUG,
    format="%(levelname)-8s [%(name)s:%(lineno)d] %(message)s",
)

# Focus on DM nodes and routing
logging.getLogger("soni.dm.nodes").setLevel(logging.DEBUG)
logging.getLogger("soni.dm.routing").setLevel(logging.DEBUG)
logging.getLogger("soni.dm.builder").setLevel(logging.DEBUG)


async def main():
    # Configure DSPy
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("ERROR: OPENAI_API_KEY not found")
        return

    lm = dspy.LM("openai/gpt-4o-mini", api_key=api_key)
    dspy.configure(lm=lm)

    # Initialize runtime
    config_path = Path("examples/flight_booking/soni.yaml")
    runtime = RuntimeLoop(config_path)
    runtime.config.settings.persistence.backend = "memory"
    await runtime._ensure_graph_initialized()

    user_id = "test_debug_loop"

    print("\n" + "=" * 70)
    print("STARTING TEST - Confirmation unclear scenario")
    print("=" * 70 + "\n")

    # Complete to confirmation
    print("Step 1: Book a flight")
    await runtime.process_message("Book a flight", user_id)

    print("\nStep 2: Boston")
    await runtime.process_message("Boston", user_id)

    print("\nStep 3: Seattle")
    await runtime.process_message("Seattle", user_id)

    print("\nStep 4: Next week")
    await runtime.process_message("Next week", user_id)

    print("\n" + "=" * 70)
    print("Step 5: Unclear response - THIS SHOULD TRIGGER THE LOOP")
    print("=" * 70 + "\n")

    try:
        response = await runtime.process_message("hmm, I'm not sure", user_id)
        print(f"\nResponse: {response}")
    except Exception as e:
        print(f"\nERROR: {type(e).__name__}: {e}")

    await runtime.cleanup()


if __name__ == "__main__":
    asyncio.run(main())
