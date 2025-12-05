"""Tests for error handling node."""

from unittest.mock import MagicMock

import pytest

from soni.core.state import create_empty_state
from soni.dm.nodes.handle_error import handle_error_node


@pytest.mark.asyncio
async def test_handle_error_validation_error():
    """Test error handling for validation errors."""
    # Arrange
    state = create_empty_state()
    state["metadata"] = {
        "error": "Invalid slot value",
        "error_type": "validation_error",
    }
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

    mock_flow_manager = MagicMock()
    mock_runtime = MagicMock()
    mock_runtime.context = {"flow_manager": mock_flow_manager}

    # Act
    result = await handle_error_node(state, mock_runtime)

    # Assert
    assert result["conversation_state"] == "idle"
    assert "try that again" in result["last_response"].lower()
    assert result["metadata"]["error"] is None
    assert result["metadata"]["error_type"] is None
    mock_flow_manager.pop_flow.assert_called_once_with(state, result="cancelled")


@pytest.mark.asyncio
async def test_handle_error_nlu_error():
    """Test error handling for NLU errors."""
    # Arrange
    state = create_empty_state()
    state["metadata"] = {
        "error": "NLU processing failed",
        "error_type": "nlu_error",
    }

    mock_flow_manager = MagicMock()
    mock_runtime = MagicMock()
    mock_runtime.context = {"flow_manager": mock_flow_manager}

    # Act
    result = await handle_error_node(state, mock_runtime)

    # Assert
    assert result["conversation_state"] == "understanding"
    assert "rephrase" in result["last_response"].lower()
    assert result["metadata"]["error"] is None
    assert result["metadata"]["error_type"] is None


@pytest.mark.asyncio
async def test_handle_error_action_error():
    """Test error handling for action errors."""
    # Arrange
    state = create_empty_state()
    state["metadata"] = {
        "error": "Action execution failed",
        "error_type": "action_error",
    }
    state["flow_stack"] = [{"flow_id": "flow_1"}]
    state["flow_slots"] = {"flow_1": {"origin": "Madrid"}}

    mock_flow_manager = MagicMock()
    mock_runtime = MagicMock()
    mock_runtime.context = {"flow_manager": mock_flow_manager}

    # Act
    result = await handle_error_node(state, mock_runtime)

    # Assert
    assert result["conversation_state"] == "idle"
    assert "try again" in result["last_response"].lower()
    assert result["flow_stack"] == []
    assert result["flow_slots"] == {}
    assert result["metadata"]["error"] is None


@pytest.mark.asyncio
async def test_handle_error_generic_error():
    """Test error handling for generic errors."""
    # Arrange
    state = create_empty_state()
    state["metadata"] = {
        "error": "Unknown error",
        "error_type": "unknown",
    }
    state["flow_stack"] = [{"flow_id": "flow_1"}]
    state["flow_slots"] = {"flow_1": {"origin": "Madrid"}}

    mock_flow_manager = MagicMock()
    mock_runtime = MagicMock()
    mock_runtime.context = {"flow_manager": mock_flow_manager}

    # Act
    result = await handle_error_node(state, mock_runtime)

    # Assert
    assert result["conversation_state"] == "idle"
    assert "start fresh" in result["last_response"].lower()
    assert result["flow_stack"] == []
    assert result["flow_slots"] == {}
    assert result["metadata"]["error"] is None


@pytest.mark.asyncio
async def test_handle_error_no_error_in_metadata():
    """Test error handling when no error in metadata."""
    # Arrange
    state = create_empty_state()
    state["metadata"] = {}

    mock_flow_manager = MagicMock()
    mock_runtime = MagicMock()
    mock_runtime.context = {"flow_manager": mock_flow_manager}

    # Act
    result = await handle_error_node(state, mock_runtime)

    # Assert
    assert result["conversation_state"] == "idle"
    assert "start fresh" in result["last_response"].lower()
