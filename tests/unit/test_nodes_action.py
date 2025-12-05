"""Tests for execute_action node."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from soni.core.state import create_empty_state
from soni.dm.nodes.execute_action import execute_action_node


@pytest.mark.asyncio
async def test_execute_action_success():
    """Test execute action with successful execution."""
    # Arrange
    state = create_empty_state()
    state["flow_stack"] = [
        {
            "flow_id": "flow_1",
            "flow_name": "book_flight",
            "flow_state": "active",
            "current_step": None,
            "outputs": {},
            "started_at": 0.0,
            "paused_at": None,
            "completed_at": None,
            "context": None,
        }
    ]
    state["flow_slots"] = {"flow_1": {"origin": "Madrid", "destination": "Barcelona"}}

    mock_action_handler = AsyncMock()
    mock_action_handler.execute.return_value = {"booking_ref": "BK-123"}

    mock_flow_manager = MagicMock()
    mock_flow_manager.get_active_context.return_value = {
        "flow_id": "flow_1",
        "flow_name": "book_flight",
    }

    mock_step_manager = MagicMock()
    mock_step_manager.get_current_step_config.return_value = MagicMock(
        type="action", call="search_available_flights"
    )
    mock_step_manager.advance_to_next_step.return_value = {}

    mock_runtime = MagicMock()
    mock_runtime.context = {
        "action_handler": mock_action_handler,
        "flow_manager": mock_flow_manager,
        "step_manager": mock_step_manager,
    }

    # Act
    result = await execute_action_node(state, mock_runtime)

    # Assert
    # conversation_state is set by advance_to_next_step based on next step type
    # Since advance_to_next_step returns {}, we check that action_result is present
    assert "action_result" in result
    # conversation_state may be set by advance_to_next_step or may be missing if flow complete
    mock_action_handler.execute.assert_called_once()


@pytest.mark.asyncio
async def test_execute_action_no_active_flow():
    """Test execute action with no active flow."""
    # Arrange
    state = create_empty_state()
    state["flow_stack"] = []

    mock_flow_manager = MagicMock()
    mock_flow_manager.get_active_context.return_value = None

    mock_step_manager = MagicMock()

    mock_runtime = MagicMock()
    mock_runtime.context = {
        "action_handler": AsyncMock(),
        "flow_manager": mock_flow_manager,
        "step_manager": mock_step_manager,
    }

    # Act
    result = await execute_action_node(state, mock_runtime)

    # Assert
    assert result["conversation_state"] == "error"
