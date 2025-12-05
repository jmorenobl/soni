"""Tests for validate_slot node."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from soni.core.state import create_empty_state
from soni.dm.nodes.validate_slot import validate_slot_node


@pytest.mark.asyncio
async def test_validate_slot_success():
    """Test validate slot with successful normalization."""
    # Arrange
    state = create_empty_state()
    state["nlu_result"] = {
        "slots": [{"name": "origin", "value": "Madrid"}],
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

    mock_normalizer = AsyncMock()
    mock_normalizer.normalize.return_value = "MAD"

    mock_flow_manager = MagicMock()
    mock_flow_manager.get_active_context.return_value = {
        "flow_id": "flow_1",
        "flow_name": "book_flight",
    }

    mock_runtime = MagicMock()
    mock_runtime.context = {
        "normalizer": mock_normalizer,
        "flow_manager": mock_flow_manager,
    }

    # Act
    result = await validate_slot_node(state, mock_runtime)

    # Assert
    assert result["conversation_state"] == "validating_slot"
    assert "flow_slots" in result
    mock_normalizer.normalize.assert_called_once()


@pytest.mark.asyncio
async def test_validate_slot_no_nlu_result():
    """Test validate slot with no NLU result."""
    # Arrange
    state = create_empty_state()
    state["nlu_result"] = None

    mock_runtime = MagicMock()
    mock_runtime.context = {
        "normalizer": AsyncMock(),
        "flow_manager": MagicMock(),
    }

    # Act
    result = await validate_slot_node(state, mock_runtime)

    # Assert
    assert result["conversation_state"] == "error"
