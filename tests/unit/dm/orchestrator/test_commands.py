"""Tests for CommandHandler pattern (OCP)."""

from typing import cast
from unittest.mock import MagicMock

import pytest

from soni.core.types import DialogueState, FlowContext, FlowDelta
from soni.dm.orchestrator.commands import (
    DEFAULT_HANDLERS,
    CancelFlowHandler,
    SetSlotHandler,
    StartFlowHandler,
)


class TestStartFlowHandler:
    """Tests for StartFlowHandler."""

    def test_can_handle_start_flow_command(self):
        """Test that handler recognizes start_flow commands."""
        # Arrange
        handler = StartFlowHandler()
        command = {"type": "start_flow", "flow_name": "transfer_funds"}

        # Act
        result = handler.can_handle(command)

        # Assert
        assert result is True

    def test_cannot_handle_other_commands(self):
        """Test that handler rejects non-start_flow commands."""
        # Arrange
        handler = StartFlowHandler()
        command = {"type": "cancel_flow"}

        # Act
        result = handler.can_handle(command)

        # Assert
        assert result is False

    @pytest.mark.asyncio
    async def test_handle_calls_push_flow(self):
        """Test that handle() calls flow_manager.push_flow()."""
        # Arrange
        handler = StartFlowHandler()
        command = {"type": "start_flow", "flow_name": "transfer_funds"}
        state = cast(DialogueState, {"flow_stack": []})
        mock_fm = MagicMock()
        mock_fm.push_flow.return_value = (
            "test_id",
            FlowDelta(
                flow_stack=[
                    cast(FlowContext, {"flow_name": "transfer_funds", "flow_id": "test_id"})
                ]
            ),
        )

        # Act
        delta = await handler.handle(command, state, mock_fm)

        # Assert
        mock_fm.push_flow.assert_called_once_with(state, "transfer_funds")
        assert delta.flow_stack is not None


class TestCancelFlowHandler:
    """Tests for CancelFlowHandler."""

    def test_can_handle_cancel_flow_command(self):
        """Test that handler recognizes cancel_flow commands."""
        # Arrange
        handler = CancelFlowHandler()
        command = {"type": "cancel_flow"}

        # Act & Assert
        assert handler.can_handle(command) is True

    @pytest.mark.asyncio
    async def test_handle_calls_pop_flow(self):
        """Test that handle() calls flow_manager.pop_flow()."""
        # Arrange
        handler = CancelFlowHandler()
        command = {"type": "cancel_flow"}
        state = cast(DialogueState, {"flow_stack": [{"flow_name": "transfer_funds"}]})
        mock_fm = MagicMock()
        mock_fm.pop_flow.return_value = (
            cast(FlowContext, {"flow_name": "transfer_funds"}),
            FlowDelta(flow_stack=[]),
        )

        # Act
        _ = await handler.handle(command, state, mock_fm)

        # Assert
        mock_fm.pop_flow.assert_called_once_with(state)


class TestSetSlotHandler:
    """Tests for SetSlotHandler."""

    def test_can_handle_set_slot_command(self):
        """Test that handler recognizes set_slot commands."""
        # Arrange
        handler = SetSlotHandler()
        command = {"type": "set_slot", "slot_name": "amount", "slot_value": "500"}

        # Act & Assert
        assert handler.can_handle(command) is True

    @pytest.mark.asyncio
    async def test_handle_calls_set_slot(self):
        """Test that handle() calls flow_manager.set_slot()."""
        # Arrange
        handler = SetSlotHandler()
        command = {"type": "set_slot", "slot_name": "amount", "slot_value": "500"}
        state = cast(DialogueState, {})
        mock_fm = MagicMock()
        mock_fm.set_slot.return_value = FlowDelta(flow_slots={"test_id": {"amount": "500"}})

        # Act
        _ = await handler.handle(command, state, mock_fm)

        # Assert
        mock_fm.set_slot.assert_called_once_with(state, "amount", "500")


class TestDefaultHandlers:
    """Tests for DEFAULT_HANDLERS list."""

    def test_default_handlers_contains_all_types(self):
        """Test that DEFAULT_HANDLERS has all required handlers."""
        # Arrange & Act
        handler_types = [type(h) for h in DEFAULT_HANDLERS]

        # Assert
        assert StartFlowHandler in handler_types
        assert CancelFlowHandler in handler_types
        assert SetSlotHandler in handler_types
