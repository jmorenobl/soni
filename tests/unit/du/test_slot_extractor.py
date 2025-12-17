"""Tests for SlotExtractor module."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from soni.core.commands import SetSlot
from soni.du.slot_extractor import SlotExtractionInput, SlotExtractor


class TestSlotExtractionInput:
    """Tests for SlotExtractionInput model."""

    def test_str_representation_basic(self):
        """GIVEN slot input WHEN str() THEN returns formatted string."""
        slot = SlotExtractionInput(
            name="amount",
            slot_type="float",
            description="Transfer amount",
        )
        result = str(slot)
        assert "amount" in result
        assert "float" in result
        assert "Transfer amount" in result

    def test_str_representation_with_examples(self):
        """GIVEN slot with examples WHEN str() THEN includes examples."""
        slot = SlotExtractionInput(
            name="beneficiary",
            slot_type="string",
            description="Recipient name",
            examples=["John", "my mom", "Maria"],
        )
        result = str(slot)
        assert "e.g." in result
        assert "John" in result


class TestSlotExtractor:
    """Tests for SlotExtractor DSPy module."""

    def test_init_without_cot(self):
        """GIVEN use_cot=False WHEN init THEN uses Predict."""
        extractor = SlotExtractor(use_cot=False)
        assert extractor is not None

    def test_init_with_cot(self):
        """GIVEN use_cot=True WHEN init THEN uses ChainOfThought."""
        extractor = SlotExtractor(use_cot=True)
        assert extractor is not None

    @pytest.mark.asyncio
    async def test_acall_returns_empty_for_no_definitions(self):
        """GIVEN empty slot definitions WHEN acall THEN returns empty list."""
        extractor = SlotExtractor(use_cot=False)
        result = await extractor.acall("some message", [])
        assert result == []

    @pytest.mark.asyncio
    async def test_acall_extracts_slots(self):
        """GIVEN message with slot values WHEN acall with mocked extractor THEN returns SetSlot commands."""
        extractor = SlotExtractor(use_cot=False)

        # Mock the DSPy extractor
        mock_result = MagicMock()
        mock_result.result.extracted_slots = [
            {"slot": "amount", "value": "100"},
            {"slot": "beneficiary_name", "value": "my mom"},
        ]
        extractor.extractor = MagicMock()
        extractor.extractor.acall = AsyncMock(return_value=mock_result)

        slot_defs = [
            SlotExtractionInput(name="amount", slot_type="float", description="Amount"),
            SlotExtractionInput(
                name="beneficiary_name", slot_type="string", description="Recipient"
            ),
        ]

        result = await extractor.acall("Transfer 100 to my mom", slot_defs)

        assert len(result) == 2
        assert all(isinstance(cmd, SetSlot) for cmd in result)
        assert result[0].slot == "amount"
        assert result[0].value == "100"
        assert result[1].slot == "beneficiary_name"
        assert result[1].value == "my mom"

    @pytest.mark.asyncio
    async def test_acall_ignores_unknown_slots(self):
        """GIVEN extraction returns unknown slot WHEN acall THEN ignores it."""
        extractor = SlotExtractor(use_cot=False)

        mock_result = MagicMock()
        mock_result.result.extracted_slots = [
            {"slot": "unknown_slot", "value": "value"},
            {"slot": "amount", "value": "50"},
        ]
        extractor.extractor = MagicMock()
        extractor.extractor.acall = AsyncMock(return_value=mock_result)

        slot_defs = [
            SlotExtractionInput(name="amount", slot_type="float", description="Amount"),
        ]

        result = await extractor.acall("Some message", slot_defs)

        assert len(result) == 1
        assert result[0].slot == "amount"

    @pytest.mark.asyncio
    async def test_acall_handles_exception_gracefully(self):
        """GIVEN extractor throws exception WHEN acall THEN returns empty list."""
        extractor = SlotExtractor(use_cot=False)

        extractor.extractor = MagicMock()
        extractor.extractor.acall = AsyncMock(side_effect=Exception("LLM error"))

        slot_defs = [
            SlotExtractionInput(name="amount", slot_type="float", description="Amount"),
        ]

        result = await extractor.acall("Some message", slot_defs)

        assert result == []

    def test_forward_sync_version(self):
        """GIVEN slot definitions WHEN forward (sync) THEN extracts slots."""
        extractor = SlotExtractor(use_cot=False)

        mock_result = MagicMock()
        mock_result.result.extracted_slots = [{"slot": "amount", "value": "100"}]
        extractor.extractor = MagicMock(return_value=mock_result)

        slot_defs = [
            SlotExtractionInput(name="amount", slot_type="float", description="Amount"),
        ]

        result = extractor.forward("Transfer 100", slot_defs)

        assert len(result) == 1
        assert result[0].slot == "amount"
