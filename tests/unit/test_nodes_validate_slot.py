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
    mock_normalizer.normalize_slot.return_value = (
        "MAD"  # Changed from normalize() to normalize_slot()
    )

    mock_flow_manager = MagicMock()
    mock_flow_manager.get_active_context.return_value = {
        "flow_id": "flow_1",
        "flow_name": "book_flight",
    }

    mock_step_manager = MagicMock()
    mock_step_manager.get_current_step_config.return_value = MagicMock(type="collect")
    mock_step_manager.is_step_complete.return_value = False  # Step not complete yet

    mock_runtime = MagicMock()
    mock_runtime.context = {
        "normalizer": mock_normalizer,
        "flow_manager": mock_flow_manager,
        "step_manager": mock_step_manager,
    }

    # Act
    result = await validate_slot_node(state, mock_runtime)

    # Assert
    # When step is not complete, conversation_state should be "waiting_for_slot"
    assert result["conversation_state"] == "waiting_for_slot"
    assert "flow_slots" in result
    mock_normalizer.normalize_slot.assert_called_once()  # Changed from normalize() to normalize_slot()


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
