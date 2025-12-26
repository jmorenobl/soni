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
