"""Interactive NLU testing script.

Run this to test NLU predictions in isolation and see what it returns.
Usage: uv run python scripts/test_nlu_interactive.py
"""

import asyncio
import os
import sys
from pathlib import Path

import dspy

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from soni.du.models import DialogueContext, MessageType, SlotAction
from soni.du.modules import SoniDU


async def test_nlu_scenario(
    user_message: str,
    context: DialogueContext,
    description: str,
):
    """Test a single NLU scenario and print results."""
    print(f"\n{'=' * 60}")
    print(f"Scenario: {description}")
    print(f"{'=' * 60}")
    print(f"User message: {user_message}")
    print("\nContext:")
    print(f"  - current_flow: {context.current_flow}")
    print(f"  - conversation_state: {context.conversation_state}")
    print(f"  - current_slots: {context.current_slots}")
    print(f"  - expected_slots: {context.expected_slots}")
    print(f"  - current_prompted_slot: {context.current_prompted_slot}")

    nlu = SoniDU()
    history = dspy.History(messages=[])

    try:
        result = await nlu.predict(user_message, history, context)

        print("\n✅ NLU Result:")
        print(f"  - message_type: {result.message_type}")
        print(f"  - command: {result.command}")
        print(f"  - confidence: {result.confidence:.2f}")
        print(f"  - confirmation_value: {result.confirmation_value}")
        print(f"  - slots ({len(result.slots)}):")
        for slot in result.slots:
            print(f"    • {slot.name} = {slot.value}")
            print(f"      action: {slot.action}, confidence: {slot.confidence:.2f}")
            if slot.previous_value:
                print(f"      previous_value: {slot.previous_value}")

        return result
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback

        traceback.print_exc()
        return None


async def main():
    """Run interactive NLU tests."""
    # Configure DSPy
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("❌ ERROR: OPENAI_API_KEY not set")
        print("Set it in .env file or environment variable")
        return

    lm = dspy.LM("openai/gpt-4o-mini", api_key=api_key)
    dspy.configure(lm=lm)
    print("✅ Configured DSPy with OpenAI")

    # Test scenarios
    scenarios = [
        {
            "description": "Slot value extraction",
            "user_message": "I want to fly to Madrid",
            "context": DialogueContext(
                current_flow="book_flight",
                expected_slots=["destination", "departure_date"],
                current_slots={},
                current_prompted_slot="destination",
                conversation_state="waiting_for_slot",
                available_flows={"book_flight": "Book a flight from origin to destination"},
                available_actions=["search_flights"],
            ),
        },
        {
            "description": "Correction detection",
            "user_message": "No, I meant Barcelona",
            "context": DialogueContext(
                current_flow="book_flight",
                expected_slots=["destination"],
                current_slots={"destination": "Madrid"},
                current_prompted_slot=None,
                conversation_state="confirming",
                available_flows={"book_flight": "Book a flight"},
                available_actions=["confirm_booking"],
            ),
        },
        {
            "description": "Confirmation (yes)",
            "user_message": "Yes, that's correct",
            "context": DialogueContext(
                current_flow="book_flight",
                expected_slots=["destination", "departure_date"],
                current_slots={"destination": "Madrid", "departure_date": "2025-12-15"},
                current_prompted_slot=None,
                conversation_state="confirming",
                available_flows={"book_flight": "Book a flight"},
                available_actions=["confirm_booking"],
            ),
        },
        {
            "description": "Confirmation (no)",
            "user_message": "No, that's wrong",
            "context": DialogueContext(
                current_flow="book_flight",
                expected_slots=["destination", "departure_date"],
                current_slots={"destination": "Madrid", "departure_date": "2025-12-15"},
                current_prompted_slot=None,
                conversation_state="confirming",
                available_flows={"book_flight": "Book a flight"},
                available_actions=["confirm_booking"],
            ),
        },
        {
            "description": "Interruption (intent change)",
            "user_message": "Actually, I want to cancel my booking",
            "context": DialogueContext(
                current_flow="book_flight",
                expected_slots=["destination"],
                current_slots={"destination": "Madrid"},
                current_prompted_slot="departure_date",
                conversation_state="waiting_for_slot",
                available_flows={
                    "book_flight": "Book a flight",
                    "cancel_booking": "Cancel an existing booking",
                },
                available_actions=["search_flights", "cancel_booking"],
            ),
        },
        {
            "description": "Digression (question)",
            "user_message": "What destinations are available?",
            "context": DialogueContext(
                current_flow="book_flight",
                expected_slots=["destination", "departure_date"],
                current_slots={},
                current_prompted_slot="destination",
                conversation_state="waiting_for_slot",
                available_flows={"book_flight": "Book a flight"},
                available_actions=["search_flights"],
            ),
        },
    ]

    print(f"\n🧪 Running {len(scenarios)} NLU test scenarios...\n")

    results = []
    for scenario in scenarios:
        result = await test_nlu_scenario(
            scenario["user_message"],
            scenario["context"],
            scenario["description"],
        )
        results.append((scenario["description"], result))

    # Summary
    print(f"\n{'=' * 60}")
    print("Summary")
    print(f"{'=' * 60}")
    for desc, result in results:
        status = "✅" if result else "❌"
        msg_type = result.message_type.value if result else "ERROR"
        print(f"{status} {desc}: {msg_type}")

    print("\n✅ Interactive NLU testing complete!")


if __name__ == "__main__":
    asyncio.run(main())
