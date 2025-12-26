from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from soni.core.commands import SetSlot
from soni.du.modules.extract_slots import SlotExtractor
from soni.du.schemas.extract_slots import SlotExtractionInput, SlotExtractionResult


class TestSlotExtractionEdgeCases:
    """Tests for slot extraction edge cases."""

    @pytest.mark.asyncio
    async def test_extract_from_empty_definitions(self, mock_llm):
        """Extraction with empty definitions should return empty list."""
        extractor = SlotExtractor()
        result = await extractor.aforward("Hello", [])
        assert result == []

    @pytest.mark.asyncio
    async def test_extract_multiple_slots(self, mock_llm):
        """Extraction should handle multiple slot definitions."""
        extractor = SlotExtractor()
        extractor.extractor = AsyncMock()

        mock_result = MagicMock()
        # dspy Prediction stores result in _store or result attribute
        mock_result.result = "dummy"
        extractor.extractor.acall.return_value = mock_result

        slot_defs = [
            SlotExtractionInput(name="amount", slot_type="number"),
            SlotExtractionInput(name="currency", slot_type="string"),
        ]

        extraction_result = SlotExtractionResult(
            extracted_slots=[
                SetSlot(slot="amount", value=100),
                SetSlot(slot="currency", value="USD"),
            ]
        )

        # Patch the function where it's USED
        with patch(
            "soni.du.modules.extract_slots.safe_extract_result", return_value=extraction_result
        ):
            result = await extractor.aforward("Transfer 100 USD", slot_defs)

        assert len(result) == 2
        assert any(s.slot == "amount" and s.value == 100 for s in result)
        assert any(s.slot == "currency" and s.value == "USD" for s in result)

    @pytest.mark.asyncio
    async def test_filters_unknown_slots(self, mock_llm):
        """Should ignore slots not in definitions."""
        extractor = SlotExtractor()
        extractor.extractor = AsyncMock()
        mock_result = MagicMock()
        mock_result.result = "dummy"
        extractor.extractor.acall.return_value = mock_result

        slot_defs = [SlotExtractionInput(name="amount", slot_type="number")]

        # LLM returns "amount" AND "unknown_slot"
        extraction_result = SlotExtractionResult(
            extracted_slots=[
                SetSlot(slot="amount", value=100),
                SetSlot(slot="unknown_slot", value="garbage"),
            ]
        )

        with patch(
            "soni.du.modules.extract_slots.safe_extract_result", return_value=extraction_result
        ):
            result = await extractor.aforward("Msg", slot_defs)

        assert len(result) == 1
        assert result[0].slot == "amount"

    @pytest.mark.asyncio
    async def test_aforward_error_handling(self, mock_llm):
        """Should return empty list on exception."""
        extractor = SlotExtractor()
        extractor.extractor = AsyncMock(side_effect=RuntimeError("LLM down"))

        result = await extractor.aforward("Hello", [SlotExtractionInput(name="s", slot_type="s")])
        assert result == []

    def test_sync_forward_empty_defs(self):
        """Sync forward should handle empty definitions."""
        extractor = SlotExtractor()
        result = extractor.forward("Hello", [])
        assert result.extracted_slots == []

    def test_sync_forward_pass(self):
        """Sync forward should return raw result for optimization."""
        extractor = SlotExtractor()
        extractor.extractor = MagicMock()

        mock_pred = MagicMock()
        mock_pred.result = "dummy"
        extractor.extractor.return_value = mock_pred

        extraction_result = SlotExtractionResult(extracted_slots=[SetSlot(slot="s", value="v")])

        with patch(
            "soni.du.modules.extract_slots.safe_extract_result", return_value=extraction_result
        ):
            result = extractor.forward("Msg", [SlotExtractionInput(name="s", slot_type="s")])

        assert len(result.extracted_slots) == 1
        assert result.extracted_slots[0].value == "v"
