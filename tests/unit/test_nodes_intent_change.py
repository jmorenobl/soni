"""Tests for handle_intent_change node."""

from unittest.mock import MagicMock

import pytest

from soni.core.state import create_empty_state
from soni.dm.nodes.handle_intent_change import handle_intent_change_node


@pytest.mark.asyncio
async def test_handle_intent_change_success():
    """Test handle intent change with valid command."""
    # Arrange
    state = create_empty_state()
    state["nlu_result"] = {
        "command": "book_flight",
    }

    mock_flow_manager = MagicMock()
    mock_flow_manager.push_flow.return_value = "flow_1"
    mock_flow_manager.get_active_context.return_value = {
        "flow_id": "flow_1",
        "flow_name": "book_flight",
        "current_step": "collect_origin",
    }

    mock_step_manager = MagicMock()
    mock_step_manager.get_current_step_config.return_value = MagicMock(
        type="collect", slot="origin"
    )

    mock_config = MagicMock()
    mock_config.flows = {"book_flight": {}}

    mock_runtime = MagicMock()
    mock_runtime.context = {
        "flow_manager": mock_flow_manager,
        "step_manager": mock_step_manager,
        "config": mock_config,
    }

    # Act
    result = await handle_intent_change_node(state, mock_runtime)

    # Assert
    assert result["conversation_state"] == "waiting_for_slot"
    mock_flow_manager.push_flow.assert_called_once()


@pytest.mark.asyncio
async def test_handle_intent_change_no_nlu_result():
    """Test handle intent change with no NLU result."""
    # Arrange
    state = create_empty_state()
    state["nlu_result"] = None

    mock_runtime = MagicMock()
    mock_runtime.context = {
        "flow_manager": MagicMock(),
    }

    # Act
    result = await handle_intent_change_node(state, mock_runtime)

    # Assert
    assert result["conversation_state"] == "error"
