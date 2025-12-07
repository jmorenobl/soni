"""Tests for handle_intent_change node."""

from unittest.mock import MagicMock

import pytest

from soni.core.state import create_empty_state
from soni.dm.nodes.handle_intent_change import handle_intent_change_node


@pytest.mark.asyncio
async def test_handle_intent_change_rejects_unknown_flow():
    """Test that handle_intent_change rejects unknown flow names."""
    # Arrange
    state = create_empty_state()
    state["nlu_result"] = {
        "command": "unknown_flow",
        "message_type": "interruption",
    }
    state["flow_stack"] = []
    state["flow_slots"] = {}

    mock_flow_manager = MagicMock()
    mock_flow_manager.get_active_context.return_value = None

    mock_config = MagicMock()
    mock_config.flows = {"book_flight": {}, "cancel_booking": {}}

    mock_runtime = MagicMock()
    mock_runtime.context = {
        "flow_manager": mock_flow_manager,
        "config": mock_config,
    }

    # Act
    result = await handle_intent_change_node(state, mock_runtime)

    # Assert
    assert result["conversation_state"] == "idle"
    assert "I don't know how to" in result["last_response"]
    assert "unknown_flow" in result["last_response"]
    # Should not have pushed flow
    mock_flow_manager.push_flow.assert_not_called()


@pytest.mark.asyncio
async def test_handle_intent_change_handles_missing_command():
    """Test that handle_intent_change handles missing command gracefully."""
    # Arrange
    state = create_empty_state()
    state["nlu_result"] = {
        "message_type": "interruption",
        # No command field
    }
    state["flow_stack"] = []
    state["flow_slots"] = {}

    mock_flow_manager = MagicMock()
    mock_config = MagicMock()
    mock_config.flows = {"book_flight": {}}

    mock_runtime = MagicMock()
    mock_runtime.context = {
        "flow_manager": mock_flow_manager,
        "config": mock_config,
    }

    # Act
    result = await handle_intent_change_node(state, mock_runtime)

    # Assert
    assert result["conversation_state"] == "idle"
    assert "I didn't understand" in result["last_response"]
    # Should not have pushed flow
    mock_flow_manager.push_flow.assert_not_called()


@pytest.mark.asyncio
async def test_handle_intent_change_starts_valid_flow():
    """Test that handle_intent_change starts a valid flow."""
    # Arrange
    state = create_empty_state()
    state["nlu_result"] = {
        "command": "book_flight",
        "message_type": "interruption",
    }
    state["flow_stack"] = []
    state["flow_slots"] = {}

    mock_flow_manager = MagicMock()
    mock_flow_manager.get_active_context.return_value = {
        "flow_id": "flow_1",
        "flow_name": "book_flight",
        "current_step": "collect_origin",
    }

    mock_step_manager = MagicMock()
    mock_step_config = MagicMock()
    mock_step_config.type = "collect"
    mock_step_config.slot = "origin"
    mock_step_manager.get_current_step_config.return_value = mock_step_config

    mock_config = MagicMock()
    mock_config.flows = {"book_flight": {}}

    mock_runtime = MagicMock()
    mock_runtime.context = {
        "flow_manager": mock_flow_manager,
        "config": mock_config,
        "step_manager": mock_step_manager,
    }

    # Act
    result = await handle_intent_change_node(state, mock_runtime)

    # Assert
    assert result["conversation_state"] == "waiting_for_slot"
    assert result["waiting_for_slot"] == "origin"
    # Should have pushed flow
    mock_flow_manager.push_flow.assert_called_once_with(
        state, flow_name="book_flight", inputs={}, reason="intent_change"
    )
