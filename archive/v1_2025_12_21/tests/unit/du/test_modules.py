"""Tests for SoniDU module."""

from unittest.mock import AsyncMock, MagicMock

import pytest
from soni.core.commands import SetSlot, StartFlow
from soni.du.models import DialogueContext, FlowInfo, NLUOutput
from soni.du.modules import SoniDU


class TestSoniDU:
    """Tests for SoniDU module."""

    @pytest.fixture
    def mock_extractor(self):
        """Mock the internal DSPy extractor."""
        extractor = AsyncMock()
        # Setup default return
        mock_result = MagicMock()
        mock_result.result = NLUOutput(commands=[])
        extractor.acall.return_value = mock_result
        return extractor

    @pytest.mark.asyncio
    async def test_extract_start_flow_command(self, mock_extractor):
        """
        GIVEN a message "I want to book a flight"
        WHEN processed by SoniDU
        THEN returns start_flow command from mocked extractor
        """
        # Arrange
        context = DialogueContext(
            available_flows=[
                FlowInfo(
                    name="book_flight",
                    description="Book a flight ticket",
                    trigger_intents=["book flight", "reserve ticket"],
                ),
            ],
            conversation_state="idle",
            available_commands=[],
        )

        du = SoniDU(use_cot=True)
        # Inject mock
        du.extractor = mock_extractor

        # Setup mock behavior - use typed StartFlow command
        expected_output = NLUOutput(commands=[StartFlow(flow_name="book_flight")])
        mock_result = MagicMock()
        mock_result.result = expected_output
        mock_extractor.acall.return_value = mock_result

        # Act
        result = await du.aforward(
            user_message="I want to book a flight",
            context=context,
        )

        # Assert
        assert len(result.commands) == 1
        assert result.commands[0].type == "start_flow"
        assert result.commands[0].flow_name == "book_flight"

        # Verify call arguments
        mock_extractor.acall.assert_called_once()
        call_kwargs = mock_extractor.acall.call_args.kwargs
        assert call_kwargs["user_message"] == "I want to book a flight"
        assert call_kwargs["context"] == context
        assert call_kwargs["history"].messages == []

    @pytest.mark.asyncio
    async def test_extract_set_slot_when_expected(self, mock_extractor):
        """
        GIVEN a context expecting "origin" slot
        WHEN user says "Madrid"
        THEN returns set_slot command from mocked extractor
        """
        # Arrange
        context = DialogueContext(
            available_flows=[],
            available_commands=[],
            active_flow="book_flight",
            expected_slot="origin",
            conversation_state="collecting",
        )
        du = SoniDU()
        du.extractor = mock_extractor

        # Setup mock behavior - use typed SetSlot command
        expected_output = NLUOutput(commands=[SetSlot(slot="origin", value="Madrid")])
        mock_result = MagicMock()
        mock_result.result = expected_output
        mock_extractor.acall.return_value = mock_result

        # Act
        result = await du.aforward(
            user_message="Madrid",
            context=context,
        )

        # Assert
        assert result.commands[0].type == "set_slot"
        assert result.commands[0].slot == "origin"
        assert result.commands[0].value == "Madrid"
