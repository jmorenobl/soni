import asyncio
import os

import dspy

from soni.du.models import DialogueContext, MessageType, SlotAction
from soni.du.modules import SoniDU

dspy.configure(lm=dspy.LM("openai/gpt-4o-mini", api_key=os.getenv("OPENAI_API_KEY")))


async def test_basic():
    # Setup
    module = SoniDU()

    # Test 1: Multi-slot extraction
    context = DialogueContext(
        current_flow="book_flight", expected_slots=["origin", "destination"], current_slots={}
    )

    result = await module.predict(
        user_message="De Madrid a Barcelona", history=dspy.History(messages=[]), context=context
    )

    print("Test 1: Multi-slot")
    print(f"  Slots: {len(result.slots)} (esperado: 2)")
    print(f"  Actions: {[s.action for s in result.slots]}")
    assert len(result.slots) == 2

    # Test 2: Correction detection
    context2 = DialogueContext(
        current_flow="book_flight",
        expected_slots=["destination"],
        current_slots={"destination": "Madrid"},
    )

    result2 = await module.predict(
        user_message="No, Barcelona", history=dspy.History(messages=[]), context=context2
    )

    print("\nTest 2: Correction")
    print(f"  Type: {result2.message_type} (esperado: CORRECTION)")
    print(f"  Action: {result2.slots[0].action} (esperado: CORRECT)")
    print(f"  Slots: {result2.slots}")
    print(f"  Previous: {result2.slots[0].previous_value} (esperado: Madrid)")
    assert result2.message_type == MessageType.CORRECTION
    assert result2.slots[0].action == SlotAction.CORRECT
    assert result2.slots[0].previous_value == "Madrid"

    print("\n✅ All tests passed!")


# Run
asyncio.run(test_basic())
