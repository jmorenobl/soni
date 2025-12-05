"""Unit tests for state validators."""

import pytest

from soni.core.errors import ValidationError
from soni.core.state import create_empty_state
from soni.core.validators import validate_state_consistency, validate_transition


def test_valid_transition_allowed():
    """Test valid transition doesn't raise error."""
    # Arrange & Act & Assert
    validate_transition("idle", "understanding")  # Should not raise


def test_invalid_transition_raises():
    """Test invalid transition raises ValidationError."""
    # Arrange & Act & Assert
    with pytest.raises(ValidationError) as exc_info:
        validate_transition("idle", "executing_action")

    assert "Invalid state transition" in str(exc_info.value)


def test_state_consistency_valid():
    """Test consistent state passes validation."""
    # Arrange
    state = create_empty_state()

    # Act & Assert
    validate_state_consistency(state)  # Should not raise


def test_state_consistency_missing_slots():
    """Test validation fails when flow has no slots."""
    # Arrange
    state = create_empty_state()
    state["flow_stack"].append(
        {
            "flow_id": "test_123",
            "flow_name": "test",
            "flow_state": "active",
            "current_step": None,
            "outputs": {},
            "started_at": 1234567890.0,
            "paused_at": None,
            "completed_at": None,
            "context": None,
        }
    )
    # Note: flow_slots is empty

    # Act & Assert
    with pytest.raises(ValidationError) as exc_info:
        validate_state_consistency(state)

    assert "missing slot storage" in str(exc_info.value)


def test_state_consistency_waiting_for_slot_without_flow():
    """Test validation fails when waiting_for_slot but no active flow."""
    # Arrange
    state = create_empty_state()
    state["waiting_for_slot"] = "destination"
    # Note: flow_stack is empty

    # Act & Assert
    with pytest.raises(ValidationError) as exc_info:
        validate_state_consistency(state)

    assert "Cannot wait for slot without active flow" in str(exc_info.value)


def test_state_consistency_waiting_state_without_slot():
    """Test validation fails when conversation_state is waiting_for_slot but waiting_for_slot is None."""
    # Arrange
    state = create_empty_state()
    state["conversation_state"] = "waiting_for_slot"
    state["waiting_for_slot"] = None

    # Act & Assert
    with pytest.raises(ValidationError) as exc_info:
        validate_state_consistency(state)

    assert "waiting_for_slot but waiting_for_slot is None" in str(exc_info.value)
