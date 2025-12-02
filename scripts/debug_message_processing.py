"""
Debug script to analyze message processing in Soni Framework.

This script simulates the e2e test to understand how messages are processed,
showing state changes and flow progression at each turn.
"""

import asyncio
import json
import logging
import os
import sys
from pathlib import Path

import dspy

try:
    from dotenv import load_dotenv

    # Load .env file if it exists
    load_dotenv()
except ImportError:
    pass  # dotenv not available, skip loading

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s - %(name)s - %(message)s",
)

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from soni.core.state import DialogueState  # noqa: E402
from soni.runtime import RuntimeLoop  # noqa: E402

# Configure DSPy with OpenAI LM if API key is available
api_key = os.getenv("OPENAI_API_KEY")
if api_key:
    lm = dspy.LM("openai/gpt-4o-mini", api_key=api_key)
    dspy.configure(lm=lm)
    print("✅ DSPy configured with OpenAI LM (gpt-4o-mini)")
else:
    print("⚠️  OPENAI_API_KEY not found - script may fail")


async def debug_conversation():
    """Debug a conversation to see state changes"""
    config_path = Path("examples/flight_booking/soni.yaml")

    print("\n" + "=" * 80)
    print("DEBUG: Message Processing Analysis")
    print("=" * 80 + "\n")

    # Create runtime
    runtime = RuntimeLoop(config_path)
    runtime.config.settings.persistence.backend = "memory"

    # Initialize graph
    await runtime._ensure_graph_initialized()

    user_id = "debug-user"
    messages = [
        "I want to book a flight",
        "New York",
        "Los Angeles",
        "Next Friday",
    ]

    try:
        for turn, msg in enumerate(messages, 1):
            print("\n" + "-" * 80)
            print(f"TURN {turn}: User says: '{msg}'")
            print("-" * 80)

            # Get state before processing
            config = {"configurable": {"thread_id": user_id}}
            state_snapshot = await runtime.graph.aget_state(config)

            if state_snapshot and state_snapshot.values:
                state_before = DialogueState.from_dict(state_snapshot.values)
                print("\n📊 STATE BEFORE:")
                print(f"  Current Flow: {state_before.current_flow}")
                print(f"  Slots: {json.dumps(state_before.slots, indent=4)}")
                print(f"  Messages: {len(state_before.messages)}")
                print(f"  Turn Count: {state_before.turn_count}")
                if state_before.trace:
                    print(f"  Last Event: {state_before.trace[-1].get('event', 'none')}")
            else:
                print("\n📊 STATE BEFORE: (New conversation)")

            # Process message
            try:
                response = await runtime.process_message(msg, user_id)
                print(f"\n🤖 RESPONSE: {response}")
            except Exception as e:
                print(f"\n❌ ERROR: {e}")
                import traceback

                traceback.print_exc()
                break

            # Get state after processing
            state_snapshot = await runtime.graph.aget_state(config)
            if state_snapshot and state_snapshot.values:
                state_after = DialogueState.from_dict(state_snapshot.values)
                print("\n📊 STATE AFTER:")
                print(f"  Current Flow: {state_after.current_flow}")
                print(f"  Slots: {json.dumps(state_after.slots, indent=4)}")
                print(f"  Messages: {len(state_after.messages)}")
                print(f"  Turn Count: {state_after.turn_count}")

                # Show recent trace events
                if state_after.trace:
                    print("\n📝 RECENT TRACE EVENTS:")
                    for event in state_after.trace[-3:]:  # Last 3 events
                        event_type = event.get("event", "unknown")
                        event_data = event.get("data", {})
                        print(f"    - {event_type}: {event_data}")

                # Show what changed
                if state_snapshot and state_snapshot.values:
                    # Compare slots
                    slots_before = state_before.slots if "state_before" in locals() else {}
                    slots_after = state_after.slots
                    if slots_before != slots_after:
                        print("\n🔄 SLOT CHANGES:")
                        for key in set(list(slots_before.keys()) + list(slots_after.keys())):
                            before_val = slots_before.get(key)
                            after_val = slots_after.get(key)
                            if before_val != after_val:
                                print(f"    {key}: {before_val} -> {after_val}")

    finally:
        await runtime.cleanup()

    print("\n" + "=" * 80)
    print("DEBUG: Analysis Complete")
    print("=" * 80 + "\n")


if __name__ == "__main__":
    asyncio.run(debug_conversation())
