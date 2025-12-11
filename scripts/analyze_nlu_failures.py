"""Analyze NLU failures in detail.

This script helps debug why specific NLU predictions fail by showing:
- Full NLU output
- Context provided
- Expected vs actual message types
- Detailed slot information

Usage: uv run python scripts/analyze_nlu_failures.py
"""

import asyncio
import json
import os
import sys
from pathlib import Path

import dspy

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from soni.du.models import DialogueContext, MessageType, SlotAction
from soni.du.modules import SoniDU


def print_section(title: str):
    """Print a formatted section header."""
    print(f"\n{'=' * 70}")
    print(f"  {title}")
    print(f"{'=' * 70}")


def print_nlu_result(result, expected_message_type: MessageType | None = None):
    """Print detailed NLU result."""
    print("\n📊 NLU Result:")
    print(f"  Message Type: {result.message_type.value}")
    if expected_message_type:
        match = "✅" if result.message_type == expected_message_type else "❌"
        print(f"  Expected: {expected_message_type.value} {match}")
    print(f"  Command: {result.command}")
    print(f"  Confidence: {result.confidence:.3f}")
    print(f"  Confirmation Value: {result.confirmation_value}")
    print(f"\n  Slots ({len(result.slots)}):")
    if result.slots:
        for i, slot in enumerate(result.slots, 1):
            print(f"    {i}. {slot.name} = '{slot.value}'")
            print(f"       Action: {slot.action.value}")
            print(f"       Confidence: {slot.confidence:.3f}")
            if slot.previous_value:
                print(f"       Previous Value: '{slot.previous_value}'")
    else:
        print("    (no slots)")

    # Print full JSON for inspection
    print("\n  Full JSON Output:")
    print(json.dumps(result.model_dump(), indent=2, default=str))


async def analyze_digression_case():
    """Analyze why digression detection fails."""
    print_section("CASE 1: Digression Detection Failure")

    # Configure DSPy
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("❌ ERROR: OPENAI_API_KEY not set")
        return

    lm = dspy.LM("openai/gpt-4o-mini", api_key=api_key)
    dspy.configure(lm=lm)

    # Test case from failing test
    nlu = SoniDU()
    user_message = "What destinations do you fly to?"

    context = DialogueContext(
        current_flow="book_flight",
        expected_slots=["destination", "departure_date"],
        current_slots={},
        current_prompted_slot="destination",
        conversation_state="waiting_for_slot",
        available_flows={"book_flight": "Book a flight"},
        available_actions=["search_flights"],
    )

    print("\n📝 Input:")
    print(f"  User Message: '{user_message}'")
    print("\n  Context:")
    print(f"    - current_flow: {context.current_flow}")
    print(f"    - conversation_state: {context.conversation_state}")
    print(f"    - current_prompted_slot: {context.current_prompted_slot}")
    print(f"    - expected_slots: {context.expected_slots}")
    print(f"    - current_slots: {context.current_slots}")
    print(f"    - available_flows: {context.available_flows}")

    # Get prediction
    result = await nlu.predict(user_message, history=dspy.History(messages=[]), context=context)

    print_nlu_result(result, expected_message_type=MessageType.DIGRESSION)

    # Analysis
    print("\n🔍 Analysis:")
    if result.message_type == MessageType.CLARIFICATION:
        print("  ❌ NLU classified as CLARIFICATION instead of DIGRESSION")
        print("\n  Question: Is this actually a clarification or a digression?")
        print("  - CLARIFICATION: User asking for clarification about the current task")
        print("  - DIGRESSION: User asking something unrelated to current task")
        print("\n  In this case:")
        print("    - User is asking about available destinations")
        print("    - This is NOT directly related to providing destination slot")
        print("    - This IS a digression from the booking flow")
        print("\n  💡 Possible reasons for misclassification:")
        print("    1. The signature/docstring may not clearly distinguish them")
        print("    2. The context may not provide enough signal")
        print("    3. The LLM may interpret 'asking about destinations' as clarification")
    elif result.message_type == MessageType.DIGRESSION:
        print("  ✅ Correctly classified as DIGRESSION")
    else:
        print(f"  ⚠️  Classified as {result.message_type.value} (unexpected)")


async def analyze_cancellation_case():
    """Analyze why cancellation detection fails."""
    print_section("CASE 2: Cancellation Detection Failure")

    # Configure DSPy
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("❌ ERROR: OPENAI_API_KEY not set")
        return

    lm = dspy.LM("openai/gpt-4o-mini", api_key=api_key)
    dspy.configure(lm=lm)

    # Test case from failing test
    nlu = SoniDU()
    user_message = "Cancel"

    context = DialogueContext(
        current_flow="book_flight",
        expected_slots=["destination", "departure_date"],
        current_slots={"destination": "Madrid"},
        current_prompted_slot="departure_date",
        conversation_state="waiting_for_slot",
        available_flows={"book_flight": "Book a flight"},
        available_actions=["search_flights"],
    )

    print("\n📝 Input:")
    print(f"  User Message: '{user_message}'")
    print("\n  Context:")
    print(f"    - current_flow: {context.current_flow}")
    print(f"    - conversation_state: {context.conversation_state}")
    print(f"    - current_prompted_slot: {context.current_prompted_slot}")
    print(f"    - expected_slots: {context.expected_slots}")
    print(f"    - current_slots: {context.current_slots}")
    print(f"    - available_flows: {context.available_flows}")
    print(f"    - available_actions: {context.available_actions}")

    # Get prediction
    result = await nlu.predict(user_message, history=dspy.History(messages=[]), context=context)

    print_nlu_result(result, expected_message_type=MessageType.CANCELLATION)

    # Analysis
    print("\n🔍 Analysis:")
    if result.message_type == MessageType.INTERRUPTION:
        print("  ❌ NLU classified as INTERRUPTION instead of CANCELLATION")
        print("\n  Question: Is this actually an interruption or a cancellation?")
        print("  - INTERRUPTION: User changing to a different intent/flow")
        print("  - CANCELLATION: User canceling the current flow/task")
        print("\n  In this case:")
        print("    - User says 'Cancel' (single word)")
        print("    - No new intent/flow mentioned")
        print("    - User wants to stop current booking flow")
        print("    - This IS a cancellation, not an interruption")
        print("\n  💡 Possible reasons for misclassification:")
        print("    1. The signature/docstring may not clearly distinguish them")
        print("    2. 'Cancel' without context may be ambiguous")
        print("    3. The LLM may need more explicit examples")
        print("    4. available_actions doesn't include 'cancel' command")
        if result.command:
            print(f"\n  📌 Note: NLU set command='{result.command}'")
            print("     This suggests it interpreted 'Cancel' as a command")
    elif result.message_type == MessageType.CANCELLATION:
        print("  ✅ Correctly classified as CANCELLATION")
    else:
        print(f"  ⚠️  Classified as {result.message_type.value} (unexpected)")


async def test_variations():
    """Test variations of the failing cases to understand patterns."""
    print_section("VARIATIONS: Testing Similar Cases")

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("❌ ERROR: OPENAI_API_KEY not set")
        return

    lm = dspy.LM("openai/gpt-4o-mini", api_key=api_key)
    dspy.configure(lm=lm)
    nlu = SoniDU()

    # Test variations for digression
    print("\n🔹 Testing Digression Variations:")
    digression_variations = [
        "What destinations do you fly to?",
        "Which cities can I travel to?",
        "Tell me about your destinations",
        "I have a question: what destinations are available?",
    ]

    context = DialogueContext(
        current_flow="book_flight",
        expected_slots=["destination", "departure_date"],
        current_slots={},
        current_prompted_slot="destination",
        conversation_state="waiting_for_slot",
        available_flows={"book_flight": "Book a flight"},
        available_actions=["search_flights"],
    )

    for msg in digression_variations:
        result = await nlu.predict(msg, history=dspy.History(messages=[]), context=context)
        status = "✅" if result.message_type == MessageType.DIGRESSION else "❌"
        print(f"  {status} '{msg}' → {result.message_type.value}")

    # Test variations for cancellation
    print("\n🔹 Testing Cancellation Variations:")
    cancellation_variations = [
        "Cancel",
        "Cancel the booking",
        "I want to cancel",
        "Never mind",
        "Forget it",
    ]

    context2 = DialogueContext(
        current_flow="book_flight",
        expected_slots=["destination", "departure_date"],
        current_slots={"destination": "Madrid"},
        current_prompted_slot="departure_date",
        conversation_state="waiting_for_slot",
        available_flows={"book_flight": "Book a flight"},
        available_actions=["search_flights"],
    )

    for msg in cancellation_variations:
        result = await nlu.predict(msg, history=dspy.History(messages=[]), context=context2)
        status = "✅" if result.message_type == MessageType.CANCELLATION else "❌"
        print(f"  {status} '{msg}' → {result.message_type.value}")


async def main():
    """Run all analyses."""
    print("\n" + "=" * 70)
    print("  NLU Failure Analysis")
    print("=" * 70)
    print("\nThis script analyzes the two failing NLU test cases in detail.")
    print("It will show what the NLU returns and help identify why it fails.\n")

    await analyze_digression_case()
    await analyze_cancellation_case()
    await test_variations()

    print_section("Summary & Recommendations")
    print("\n📋 Next Steps:")
    print("  1. Review the NLU signature/docstring for clarity")
    print("  2. Check if examples in the signature distinguish these cases")
    print("  3. Consider if test expectations match actual use cases")
    print("  4. May need to adjust signature or add more context")
    print("\n✅ Analysis complete!")


if __name__ == "__main__":
    asyncio.run(main())
