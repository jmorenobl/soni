"""Debug NLU intent detection for 'I want to book a flight' message."""

import asyncio
import os

import dspy
from dotenv import load_dotenv

from soni.du.models import DialogueContext, MessageType
from soni.du.modules import SoniDU

# Load environment
load_dotenv()

# Configure DSPy with real LM
api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    print("ERROR: OPENAI_API_KEY not set")
    exit(1)

lm = dspy.LM("openai/gpt-4o-mini", api_key=api_key)
dspy.configure(lm=lm)


async def main():
    """Test NLU classification for intent detection."""
    print("=" * 80)
    print("NLU Intent Detection Debug")
    print("=" * 80)

    nlu = SoniDU(use_cot=True)

    # Scenario: User says "I want to book a flight" with NO active flow
    user_message = "I want to book a flight"

    context = DialogueContext(
        current_flow="none",  # No active flow (must be string, not None)
        expected_slots=[],
        current_slots={},
        current_prompted_slot=None,
        conversation_state="idle",  # Starting state
        available_flows={"book_flight": "Book a flight from origin to destination"},
        available_actions=[],
    )

    history = dspy.History(messages=[])

    print("\n📝 Input:")
    print(f"  User message: '{user_message}'")
    print(f"  Current flow: {context.current_flow}")
    print(f"  Conversation state: {context.conversation_state}")
    print(f"  Available flows: {list(context.available_flows.keys())}")

    print("\n🔍 Calling NLU...")
    result = await nlu.predict(user_message, history, context)

    print("\n📊 NLU Result:")
    print(f"  message_type: {result.message_type}")
    print(f"  command: {result.command}")
    print(f"  slots: {result.slots}")
    print(f"  confidence: {result.confidence}")

    print("\n❓ Expected:")
    print(f"  message_type: {MessageType.INTERRUPTION} or {MessageType.CONTINUATION}")
    print("  command: 'book_flight'")

    print("\n✅ Actual:")
    print(f"  message_type: {result.message_type}")
    print(f"  command: {result.command}")

    if result.message_type == MessageType.INTERRUPTION and result.command == "book_flight":
        print("\n✅ CORRECT: NLU detected intent correctly")
    elif result.message_type == MessageType.CONTINUATION and result.command == "book_flight":
        print("\n⚠️  PARTIAL: NLU detected command but used CONTINUATION instead of INTERRUPTION")
    elif result.command == "book_flight":
        print(f"\n⚠️  PARTIAL: NLU detected command but wrong message_type: {result.message_type}")
    else:
        print("\n❌ FAIL: NLU did not detect intent correctly")
        print(f"   Expected command='book_flight', got command={result.command}")
        print(f"   Expected message_type=INTERRUPTION, got message_type={result.message_type}")

    # Test with different phrasing
    print("\n" + "=" * 80)
    print("Testing alternative phrasing: 'Book a flight'")
    print("=" * 80)

    result2 = await nlu.predict("Book a flight", history, context)
    print(f"  message_type: {result2.message_type}")
    print(f"  command: {result2.command}")

    print("\n" + "=" * 80)
    print("Testing with active flow (should be different)")
    print("=" * 80)

    context_with_flow = DialogueContext(
        current_flow="book_hotel",  # Different flow active
        expected_slots=["location"],
        current_slots={},
        current_prompted_slot="location",
        conversation_state="waiting_for_slot",
        available_flows={"book_flight": "Book a flight", "book_hotel": "Book a hotel"},
        available_actions=[],
    )

    result3 = await nlu.predict("I want to book a flight", history, context_with_flow)
    print(f"  message_type: {result3.message_type}")
    print(f"  command: {result3.command}")
    print("  Expected: INTERRUPTION with command='book_flight' (switching from hotel to flight)")


if __name__ == "__main__":
    asyncio.run(main())
