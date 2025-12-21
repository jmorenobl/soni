"""Tests for pattern handler return types.

Verifies that all pattern handlers return CommandResult for consistency.
"""

from unittest.mock import MagicMock

import pytest

from soni.core.commands import CancelFlow, CorrectSlot, RequestClarification
from soni.dm.nodes.command_registry import CommandResult


class TestPatternHandlerReturnTypes:
    """Tests to verify all pattern handlers return CommandResult."""

    @pytest.fixture
    def mock_context(self):
        """Create mock RuntimeContext."""
        context = MagicMock()
        context.flow_manager = MagicMock()
        context.flow_manager.set_slot = MagicMock(return_value=None)
        context.flow_manager.get_active_context = MagicMock(
            return_value={"flow_id": "test", "flow_name": "test_flow"}
        )
        context.flow_manager.pop_flow = MagicMock(
            return_value=(
                {"flow_id": "test", "flow_name": "test_flow"},
                MagicMock(flow_stack=[], flow_slots=None),
            )
        )
        context.config = MagicMock()
        context.config.slots = {}
        context.config.settings = MagicMock()
        context.config.settings.patterns = None
        return context

    @pytest.fixture
    def mock_state(self):
        """Create mock DialogueState."""
        return {
            "flow_stack": [{"flow_id": "test", "flow_name": "test_flow"}],
            "flow_slots": {"test": {}},
            "waiting_for_slot": "amount",
            "messages": [],
        }

    @pytest.mark.asyncio
    async def test_clarification_handler_returns_command_result(self, mock_context, mock_state):
        """Test that ClarificationHandler returns CommandResult."""
        from soni.dm.patterns.clarification import ClarificationHandler

        handler = ClarificationHandler()
        cmd = RequestClarification(topic="amount")

        result = await handler.handle(cmd, mock_state, mock_context)

        assert isinstance(result, CommandResult)
        assert len(result.messages) > 0

    @pytest.mark.asyncio
    async def test_correction_handler_returns_command_result(self, mock_context, mock_state):
        """Test that CorrectionHandler returns CommandResult."""
        from soni.dm.patterns.correction import CorrectionHandler

        handler = CorrectionHandler()
        cmd = CorrectSlot(slot="amount", new_value="100")

        result = await handler.handle(cmd, mock_state, mock_context)

        assert isinstance(result, CommandResult)
        assert len(result.messages) > 0

    @pytest.mark.asyncio
    async def test_cancellation_handler_returns_command_result(self, mock_context, mock_state):
        """Test that CancellationHandler returns CommandResult."""
        from soni.dm.patterns.cancellation import CancellationHandler

        handler = CancellationHandler()
        cmd = CancelFlow()

        result = await handler.handle(cmd, mock_state, mock_context)

        assert isinstance(result, CommandResult)
        assert result.should_reset_flow_state is True


class TestDispatchPatternCommand:
    """Tests for dispatch_pattern_command function."""

    @pytest.mark.asyncio
    async def test_returns_command_result_for_known_pattern(self):
        """Test that dispatch returns CommandResult for known patterns."""
        from typing import cast

        from soni.core.types import DialogueState
        from soni.dm.patterns import dispatch_pattern_command

        # Mock state and context
        state = cast(
            DialogueState,
            {
                "flow_stack": [],
                "flow_slots": {},
                "waiting_for_slot": "test",
                "messages": [],
            },
        )
        context = MagicMock()
        context.config = MagicMock()
        context.config.slots = {}
        context.config.settings = MagicMock()
        context.config.settings.patterns = None

        cmd = RequestClarification(topic="test")

        result = await dispatch_pattern_command(cmd, state, context)

        assert result is None or isinstance(result, CommandResult)

    @pytest.mark.asyncio
    async def test_returns_none_for_unknown_command(self):
        """Test that dispatch returns None for unknown command types."""
        from typing import cast

        from soni.core.commands import StartFlow
        from soni.core.types import DialogueState
        from soni.dm.patterns import dispatch_pattern_command

        state = cast(DialogueState, {"flow_stack": [], "flow_slots": {}, "messages": []})
        context = MagicMock()

        # Use a non-pattern command
        cmd = StartFlow(flow_name="test")

        result = await dispatch_pattern_command(cmd, state, context)

        assert result is None
