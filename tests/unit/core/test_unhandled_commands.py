"""Tests for command handling in understand_node.

Tests verify that handled commands are properly processed,
and unhandled commands trigger appropriate debug logs.
"""

import logging
from unittest.mock import AsyncMock, MagicMock

import pytest
from pydantic import BaseModel

from soni.core.types import RuntimeContext
from soni.dm.nodes.understand import understand_node


class UnknownCommand(BaseModel):
    """A custom command type not handled by understand_node."""

    type: str = "unknown_custom_command"


@pytest.mark.asyncio
async def test_log_debug_for_unhandled_command_type(caplog):
    """Test that truly unknown command types trigger debug logs in understand_node.

    Note: CancelFlow IS now handled via the patterns system.
    This test uses a custom command type that is genuinely unhandled.
    """
    # Arrange
    caplog.set_level(logging.DEBUG)

    from soni.core.constants import FlowState
    from soni.core.state import create_empty_dialogue_state

    state = create_empty_dialogue_state()
    state.update(
        {
            "user_message": "something weird",
            "flow_state": FlowState.ACTIVE,
        }
    )

    # Mock NLU output with a custom unknown command
    mock_du = MagicMock()
    mock_du.acall = AsyncMock(return_value=MagicMock(commands=[UnknownCommand()]))

    mock_fm = MagicMock()
    mock_fm.get_active_context.return_value = None
    # Set up synchronous mocks for new FlowManager API
    mock_fm.set_slot = MagicMock(return_value=None)
    mock_fm.handle_intent_change = MagicMock(return_value=None)

    mock_config = MagicMock()
    mock_config.slots = {}
    mock_config.flows = {}

    context = RuntimeContext(
        config=mock_config, flow_manager=mock_fm, du=mock_du, action_handler=MagicMock()
    )

    from langchain_core.runnables import RunnableConfig

    config: RunnableConfig = {"configurable": {"runtime_context": context}}

    # Act
    await understand_node(state, config)

    # Assert - Unknown commands trigger warning from registry
    assert "No handler registered for command type" in caplog.text
