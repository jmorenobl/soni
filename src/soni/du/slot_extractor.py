"""Slot extraction module for two-pass NLU.

Pass 2 of the two-pass NLU system. Given a user message and slot definitions
for a specific flow, extracts slot values mentioned in the message.

This module is called ONLY when Pass 1 (SoniDU) detects a StartFlow command.
"""

import logging
from typing import Any

import dspy
from pydantic import BaseModel, Field

from soni.core.commands import SetSlot

logger = logging.getLogger(__name__)


class SlotExtractionInput(BaseModel):
    """Input for slot extraction."""

    name: str = Field(description="Slot identifier")
    slot_type: str = Field(description="Data type: string, float, date, city, etc.")
    description: str = Field(default="", description="What this slot expects")
    examples: list[str] = Field(default_factory=list, description="Example valid values")

    def __str__(self) -> str:
        examples_str = f" (e.g., {', '.join(self.examples[:3])})" if self.examples else ""
        return f"- {self.name} ({self.slot_type}): {self.description}{examples_str}"


class SlotExtractionResult(BaseModel):
    """Result of slot extraction."""

    extracted_slots: list[dict[str, Any]] = Field(
        default_factory=list,
        description="List of extracted slots with 'slot' and 'value' keys",
    )


class ExtractSlots(dspy.Signature):
    """Extract slot values from user message given slot definitions.

    You are extracting entity values from a user message for a dialogue system.
    Given a list of slot definitions, identify any values mentioned in the message.

    RULES:
    1. Only extract slots that are EXPLICITLY mentioned in the message
    2. Do not infer or guess values that are not clearly stated
    3. Match slot types appropriately (e.g., "100" for amount, "my mom" for person)
    4. If no slots are found, return an empty list
    5. Return slots in the format: {"slot": "slot_name", "value": "extracted_value"}

    Examples:
    - "Transfer 100€ to my mom" → [{"slot": "amount", "value": "100"}, {"slot": "beneficiary_name", "value": "my mom"}]
    - "I want to make a transfer" → [] (no specific values mentioned)
    - "Send money to account ES1234567890" → [{"slot": "iban", "value": "ES1234567890"}]
    """

    user_message: str = dspy.InputField(desc="The user's message to extract slots from")
    slot_definitions: list[SlotExtractionInput] = dspy.InputField(
        desc="Available slots to extract with their types and descriptions"
    )

    result: SlotExtractionResult = dspy.OutputField(desc="Extracted slots matching the definitions")


class SlotExtractor(dspy.Module):
    """Slot extraction module for Pass 2 of two-pass NLU.

    Features:
    - Focused extraction using flow-specific slot definitions
    - Lightweight compared to full NLU (no intent detection)
    - Returns SetSlot commands ready to merge with Pass 1 results
    """

    def __init__(self, use_cot: bool = False):
        """Initialize SlotExtractor.

        Args:
            use_cot: If True, use ChainOfThought for reasoning.
                     Default False since extraction is simpler than intent detection.
        """
        super().__init__()
        if use_cot:
            self.extractor = dspy.ChainOfThought(ExtractSlots)
        else:
            self.extractor = dspy.Predict(ExtractSlots)

    async def acall(
        self,
        user_message: str,
        slot_definitions: list[SlotExtractionInput],
    ) -> list[SetSlot]:
        """Extract slots from user message (async).

        Args:
            user_message: The user's input message
            slot_definitions: Slot definitions for the target flow

        Returns:
            List of SetSlot commands for extracted values
        """
        if not slot_definitions:
            return []

        try:
            result = await self.extractor.acall(
                user_message=user_message,
                slot_definitions=slot_definitions,
            )

            # Convert extraction result to SetSlot commands
            extracted: list[SetSlot] = []
            for slot_data in result.result.extracted_slots:
                slot_name = slot_data.get("slot")
                slot_value = slot_data.get("value")

                if slot_name and slot_value is not None:
                    # Validate that slot exists in definitions
                    valid_names = {s.name for s in slot_definitions}
                    if slot_name in valid_names:
                        extracted.append(SetSlot(slot=slot_name, value=slot_value))
                    else:
                        logger.warning(
                            f"SlotExtractor returned unknown slot '{slot_name}', ignoring"
                        )

            logger.debug(f"SlotExtractor extracted {len(extracted)} slots from message")
            return extracted

        except Exception as e:
            logger.error(f"Slot extraction failed: {e}", exc_info=True)
            return []

    def forward(
        self,
        user_message: str,
        slot_definitions: list[SlotExtractionInput],
    ) -> list[SetSlot]:
        """Sync version (for testing/optimization)."""
        if not slot_definitions:
            return []

        result = self.extractor(
            user_message=user_message,
            slot_definitions=slot_definitions,
        )

        extracted: list[SetSlot] = []
        for slot_data in result.result.extracted_slots:
            slot_name = slot_data.get("slot")
            slot_value = slot_data.get("value")

            if slot_name and slot_value is not None:
                valid_names = {s.name for s in slot_definitions}
                if slot_name in valid_names:
                    extracted.append(SetSlot(slot=slot_name, value=slot_value))

        return extracted
