"""Tests for CommandHandlerRegistry."""

from typing import Any
from unittest.mock import Mock

import pytest
from soni.core.commands import (
    AffirmConfirmation,
    ChitChat,
    ClearSlot,
    CompleteFlow,
    DenyConfirmation,
    SetSlot,
    StartFlow,
)
from soni.dm.nodes.command_registry import (
    COMMAND_HANDLERS,
    CommandHandlerRegistry,
    CommandResult,
    register_command_handler,
)


class TestCommandHandlerRegistry:
    """Test command registry functionality."""

    @pytest.fixture
    def registry(self):
        return CommandHandlerRegistry()

    @pytest.fixture
    def mock_context(self):
        ctx = Mock()
        ctx.flow_manager = Mock()
        ctx.flow_manager.handle_intent_change = Mock(return_value=None)
        ctx.flow_manager.set_slot = Mock(return_value=None)
        ctx.flow_manager.pop_flow = Mock(return_value=(None, None))
        return ctx

    @pytest.fixture
    def empty_state(self):
        return {
            "flow_stack": [],
            "flow_slots": {},
            "messages": [],
        }


class TestHandlerRegistration:
    """Test handler registration."""

    def test_all_command_types_have_handlers(self):
        """Every command type should have a handler."""
        command_types = [
            StartFlow,
            SetSlot,
            CompleteFlow,
            ClearSlot,
            ChitChat,
            AffirmConfirmation,
            DenyConfirmation,
        ]

        for cmd_type in command_types:
            assert cmd_type in COMMAND_HANDLERS, f"Missing handler for {cmd_type}"

    def test_register_custom_handler(self):
        """Should be able to register custom handlers."""

        class CustomCommand:
            type = "custom"

        class CustomHandler:
            async def handle(self, cmd, state, context, expected_slot):
                return CommandResult()

        register_command_handler(CustomCommand, CustomHandler())

        assert CustomCommand in COMMAND_HANDLERS


class TestStartFlowHandler:
    """Test StartFlow command handling."""

    @pytest.fixture
    def registry(self):
        return CommandHandlerRegistry()

    @pytest.mark.asyncio
    async def test_does_not_mutate_state_directly(self, registry):
        """Handler should NOT mutate state - only return updates."""
        ctx = Mock()
        ctx.flow_manager.handle_intent_change = Mock(
            return_value=Mock(
                flow_stack=[{"flow_name": "test"}],
                flow_slots={"id": {}},
            )
        )

        state: dict[str, Any] = {"flow_stack": [], "flow_slots": {}}
        original_stack = state["flow_stack"]
        original_slots = state["flow_slots"]

        cmd = StartFlow(flow_name="test")
        result = await registry.dispatch(cmd, state, ctx, None)

        # State should NOT be mutated
        assert state["flow_stack"] is original_stack
        assert state["flow_slots"] is original_slots

        # Updates should be in result
        assert "flow_stack" in result.updates or "flow_slots" in result.updates


class TestCompleteFlowHandler:
    """Test CompleteFlow command handling."""

    @pytest.fixture
    def registry(self):
        return CommandHandlerRegistry()

    @pytest.mark.asyncio
    async def test_pops_current_flow(self, registry):
        """CompleteFlow should pop the current flow."""
        ctx = Mock()
        ctx.flow_manager.pop_flow = Mock(
            return_value=(
                {"flow_name": "completed"},
                Mock(flow_stack=[]),
            )
        )

        state = {"flow_stack": [{"flow_name": "test"}], "flow_slots": {}}
        cmd = CompleteFlow()

        _result = await registry.dispatch(cmd, state, ctx, None)

        ctx.flow_manager.pop_flow.assert_called_once()


class TestChitChatHandler:
    """Test ChitChat command handling."""

    @pytest.fixture
    def registry(self):
        return CommandHandlerRegistry()

    @pytest.mark.asyncio
    async def test_returns_message(self, registry):
        """ChitChat should return a message."""
        ctx = Mock()
        state: dict[str, Any] = {"flow_stack": [], "flow_slots": {}, "messages": []}
        cmd = ChitChat(message="Hello!")

        result = await registry.dispatch(cmd, state, ctx, None)

        assert len(result.messages) > 0
        assert "Hello" in result.messages[0].content or "help" in result.messages[0].content.lower()


class TestUnhandledCommands:
    """Test handling of unknown command types."""

    @pytest.fixture
    def registry(self):
        return CommandHandlerRegistry()

    @pytest.mark.asyncio
    async def test_returns_none_for_unknown_command(self, registry):
        """Unknown command types should return None."""

        class UnknownCommand:
            type = "unknown"

        ctx = Mock()
        state: dict[str, Any] = {}

        result = await registry.dispatch(UnknownCommand(), state, ctx, None)

        assert result is None
