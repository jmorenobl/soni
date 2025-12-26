"""DSPy signature for slot extraction."""

import dspy

from soni.du.schemas.extract_slots import SlotExtractionInput, SlotExtractionResult


class ExtractSlots(dspy.Signature):
    """Extract slot values from a user message based on slot definitions."""

    user_message: str = dspy.InputField(desc="The user's message to extract slots from")
    slot_definitions: list[SlotExtractionInput] = dspy.InputField(
        desc="Available slots to extract with their types and descriptions"
    )

    result: SlotExtractionResult = dspy.OutputField(desc="Extracted slots matching the definitions")
