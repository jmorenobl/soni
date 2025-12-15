#!/usr/bin/env python3
"""Debug script for confirmation flow recursion issue.

Reproduces the failing test_confirmation_unclear_then_yes to trace the routing loop.
"""

import asyncio
import logging
import os
import sys

import dspy

# Ensure src is in python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../src")))

from soni.core.config import SoniConfig
from soni.runtime.runtime import RuntimeLoop


async def debug_confirmation_flow():
    """Debug the confirmation flow recursion issue."""
    print("=== Debugging Confirmation Flow Recursion ===\n")

    config_path = "examples/flight_booking/soni.yaml"
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("Error: OPENAI_API_KEY required")
        return

    # Enable detailed logging
    logging.basicConfig(
        level=logging.DEBUG,
        format="%(name)s:%(lineno)d - %(message)s",
    )
    # Focus on routing and key nodes
    logging.getLogger("soni.dm.routing").setLevel(logging.DEBUG)
    logging.getLogger("soni.dm.nodes").setLevel(logging.DEBUG)
    logging.getLogger("soni.flow").setLevel(logging.DEBUG)
    logging.getLogger("soni.runtime").setLevel(logging.INFO)
    # Quiet noisy loggers
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("dspy").setLevel(logging.WARNING)
    logging.getLogger("openai").setLevel(logging.WARNING)

    # Configure DSPy
    try:
        soni_config = SoniConfig.from_yaml(config_path)
        nlu_config = soni_config.settings.models.nlu
        lm = dspy.LM(f"{nlu_config.provider}/{nlu_config.model}", api_key=api_key)
        dspy.configure(lm=lm)
    except Exception as e:
        print(f"Error config: {e}")
        return

    # Runtime - match test fixture configuration
    runtime = RuntimeLoop(config_path)
    runtime.config.settings.persistence.backend = "memory"  # Match test fixture
    await runtime._ensure_graph_initialized()

    user_id = "debug-confirmation"

    try:
        # Mimic the failing test sequence
        turns = [
            "Book a flight",
            "Boston",  # origin
            "Seattle",  # destination
            "Next week",  # departure_date - gets to confirmation
            "hmm, I'm not sure",  # unclear response - THIS IS WHERE IT FAILS
        ]

        for i, msg in enumerate(turns):
            print(f"\n{'=' * 60}")
            print(f"TURN {i}: '{msg}'")
            print("=" * 60)

            try:
                response = await runtime.process_message(msg, user_id)
                print(f"\nAssistant: {response}")

                # Get state for analysis
                state = await runtime.graph.aget_state({"configurable": {"thread_id": user_id}})
                print(f"\n[State After Turn {i}]")
                print(
                    f"  flow_stack: {[f['flow_name'] for f in state.values.get('flow_stack', [])]}"
                )
                print(f"  conversation_state: {state.values.get('conversation_state')}")
                print(f"  waiting_for_slot: {state.values.get('waiting_for_slot')}")
                print(f"  current_step: {state.values.get('current_step')}")
                print(f"  user_message: '{state.values.get('user_message', '')[:30]}...'")
                nlu = state.values.get("nlu_result", {})
                if nlu:
                    print(f"  nlu_result: type={nlu.get('message_type')}, cmd={nlu.get('command')}")

            except Exception as e:
                print(f"\n❌ ERROR on turn {i}: {e}")
                # Get state even on error
                try:
                    state = await runtime.graph.aget_state({"configurable": {"thread_id": user_id}})
                    print("\n[State At Error]")
                    print(
                        f"  flow_stack: {[f['flow_name'] for f in state.values.get('flow_stack', [])]}"
                    )
                    print(f"  conversation_state: {state.values.get('conversation_state')}")
                    print(f"  waiting_for_slot: {state.values.get('waiting_for_slot')}")
                    print(f"  current_step: {state.values.get('current_step')}")
                except Exception:
                    pass
                break

    finally:
        await runtime.cleanup()


if __name__ == "__main__":
    asyncio.run(debug_confirmation_flow())
