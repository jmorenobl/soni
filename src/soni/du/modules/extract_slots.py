"""Slot extraction module for two-pass NLU."""

import logging

import dspy

from soni.core.commands import SetSlot
from soni.du.base import OptimizableDSPyModule, safe_extract_result
from soni.du.schemas.extract_slots import SlotExtractionInput, SlotExtractionResult
from soni.du.signatures.extract_slots import ExtractSlots

logger = logging.getLogger(__name__)


class SlotExtractor(OptimizableDSPyModule):
    """Slot extraction module for Pass 2 of two-pass NLU.

    Features:
    - Focused extraction using flow-specific slot definitions
    - Lightweight compared to full NLU (no intent detection)
    - Returns SetSlot commands ready to merge with Pass 1 results
    - Support for optimization and persistence
    """

    # Priority-ordered optimization files
    optimized_files = [
        "slot_extractor_gepa.json",
        "slot_extractor_miprov2.json",
        "baseline_v1_slots_gepa.json",
        "baseline_v1_slots_miprov2.json",
        "optimized_slot_extractor.json",
    ]

    # Default: no ChainOfThought (extraction is simpler)
    default_use_cot = False

    def _create_extractor(self, use_cot: bool) -> dspy.Module:
        """Create the slot extractor predictor."""
        if use_cot:
            return dspy.ChainOfThought(ExtractSlots)
        return dspy.Predict(ExtractSlots)

    async def aforward(
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

        result = await self.extractor.acall(
            user_message=user_message,
            slot_definitions=slot_definitions,
        )

        # Validate extraction result
        extraction_result = safe_extract_result(
            result.result,
            SlotExtractionResult,
            default_factory=lambda: SlotExtractionResult(extracted_slots=[]),
            context="Slot extraction",
        )

        # Filter by valid slot names
        valid_names = {s.name for s in slot_definitions}
        extracted = [slot for slot in extraction_result.extracted_slots if slot.slot in valid_names]

        for slot in extraction_result.extracted_slots:
            if slot.slot not in valid_names:
                logger.warning(f"SlotExtractor returned unknown slot '{slot.slot}', ignoring")

        logger.debug(f"SlotExtractor extracted {len(extracted)} slots from message")
        return extracted

    def forward(
        self,
        user_message: str,
        slot_definitions: list[SlotExtractionInput],
    ) -> SlotExtractionResult:
        """Sync version (for testing/optimization).

        Note: Optimization uses raw Signature output (SlotExtractionResult),
        not SetSlot commands directly, because Metrics need structured I/O.
        """
        if not slot_definitions:
            return SlotExtractionResult(extracted_slots=[])

        result = self.extractor(
            user_message=user_message,
            slot_definitions=slot_definitions,
        )

        return safe_extract_result(
            result.result,
            SlotExtractionResult,
            default_factory=lambda: SlotExtractionResult(extracted_slots=[]),
            context="Slot extraction forward pass",
        )
