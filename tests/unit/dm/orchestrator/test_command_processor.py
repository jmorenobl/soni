"""Tests for CommandProcessor (SRP)."""

from typing import cast
from unittest.mock import MagicMock

import pytest

from soni.core.types import DialogueState, FlowContext, FlowDelta
from soni.dm.orchestrator.command_processor import CommandProcessor
from soni.dm.orchestrator.commands import DEFAULT_HANDLERS


class TestCommandProcessor:
    """Tests for CommandProcessor."""

    @pytest.mark.asyncio
    async def test_process_empty_commands_returns_empty_delta(self):
        """Test that processing no commands returns empty delta."""
        # Arrange
        processor = CommandProcessor(DEFAULT_HANDLERS)
        mock_fm = MagicMock()

        # Act
        delta = await processor.process(
            commands=[], state=cast(DialogueState, {}), flow_manager=mock_fm
        )

        # Assert
        assert delta.flow_stack is None
        assert delta.flow_slots is None

    @pytest.mark.asyncio
    async def test_process_delegates_to_correct_handler(self):
        """Test that commands are routed to correct handlers."""
        # Arrange
        processor = CommandProcessor(DEFAULT_HANDLERS)
        commands = [{"type": "start_flow", "flow_name": "check_balance"}]
        state = cast(DialogueState, {"flow_stack": []})
        mock_fm = MagicMock()
        mock_fm.push_flow.return_value = (
            "test_id",
            FlowDelta(
                flow_stack=[cast(FlowContext, {"flow_name": "check_balance", "flow_id": "test_id"})]
            ),
        )

        # Act
        delta = await processor.process(commands, state, mock_fm)

        # Assert
        mock_fm.push_flow.assert_called_once()
        assert delta.flow_stack is not None

    @pytest.mark.asyncio
    async def test_process_handles_multiple_commands(self):
        """Test that multiple commands are all processed."""
        # Arrange
        processor = CommandProcessor(DEFAULT_HANDLERS)
        commands = [
            {"type": "start_flow", "flow_name": "transfer"},
            {"type": "set_slot", "slot": "amount", "value": "100"},
        ]
        mock_fm = MagicMock()
        mock_fm.push_flow.return_value = ("test_id", FlowDelta(flow_stack=[]))
        mock_fm.set_slot.return_value = FlowDelta(flow_slots={"test_id": {"amount": "100"}})

        # Act
        _ = await processor.process(commands, cast(DialogueState, {}), mock_fm)

        # Assert
        assert mock_fm.push_flow.called
        assert mock_fm.set_slot.called
