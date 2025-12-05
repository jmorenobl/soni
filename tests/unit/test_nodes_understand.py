"""Tests for understand node."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from soni.core.state import create_initial_state
from soni.dm.nodes.understand import understand_node


@pytest.mark.asyncio
async def test_understand_node_calls_nlu():
    """Test understand node calls NLU provider."""
    # Arrange
    state = create_initial_state("Hello")

    # Mock runtime context
    mock_nlu = AsyncMock()
    mock_nlu.understand.return_value = {
        "message_type": "interruption",
        "command": "greet",
        "slots": [],
        "confidence": 0.9,
        "reasoning": "greeting",
    }

    mock_flow_manager = MagicMock()
    mock_flow_manager.get_active_context.return_value = None

    mock_scope_manager = MagicMock()
    mock_scope_manager.get_available_actions.return_value = ["greet"]
    mock_scope_manager.get_available_flows.return_value = []

    mock_runtime = MagicMock()
    mock_runtime.context = {
        "nlu_provider": mock_nlu,
        "flow_manager": mock_flow_manager,
        "scope_manager": mock_scope_manager,
    }

    # Act
    result = await understand_node(state, mock_runtime)

    # Assert
    assert result["conversation_state"] == "understanding"
    assert result["nlu_result"]["command"] == "greet"
    mock_nlu.understand.assert_called_once()
    assert "last_nlu_call" in result


@pytest.mark.asyncio
async def test_understand_node_with_active_flow():
    """Test understand node with active flow context."""
    # Arrange
    state = create_initial_state("I want to book a flight")
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
    state["flow_slots"] = {"flow_1": {"origin": "Madrid"}}

    mock_nlu = AsyncMock()
    mock_nlu.understand.return_value = {
        "message_type": "slot_value",
        "command": "book_flight",
        "slots": [{"name": "destination", "value": "Barcelona"}],
        "confidence": 0.95,
        "reasoning": "destination provided",
    }

    mock_flow_manager = MagicMock()
    mock_flow_manager.get_active_context.return_value = {
        "flow_id": "flow_1",
        "flow_name": "book_flight",
    }

    mock_scope_manager = MagicMock()
    mock_scope_manager.get_available_actions.return_value = ["book_flight"]
    mock_scope_manager.get_available_flows.return_value = ["book_flight"]

    mock_runtime = MagicMock()
    mock_runtime.context = {
        "nlu_provider": mock_nlu,
        "flow_manager": mock_flow_manager,
        "scope_manager": mock_scope_manager,
    }

    # Act
    result = await understand_node(state, mock_runtime)

    # Assert
    assert result["nlu_result"]["message_type"] == "slot_value"
    # Verify dialogue context includes current slots
    call_args = mock_nlu.understand.call_args
    assert call_args[0][0] == "I want to book a flight"
    dialogue_context = call_args[0][1]
    assert dialogue_context["current_flow"] == "book_flight"
    assert "origin" in dialogue_context["current_slots"]
