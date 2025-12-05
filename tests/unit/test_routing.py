"""Tests for routing functions."""

import pytest

from soni.core.state import create_empty_state
from soni.dm.routing import route_after_understand, route_after_validate


def test_route_after_understand_slot_value():
    """Test routing with slot_value message type."""
    # Arrange
    state = create_empty_state()
    state["nlu_result"] = {
        "message_type": "slot_value",
        "command": "book_flight",
        "slots": [{"name": "origin", "value": "Madrid"}],
    }

    # Act
    next_node = route_after_understand(state)

    # Assert
    assert next_node == "validate_slot"


def test_route_after_understand_interruption():
    """Test routing with interruption message type."""
    # Arrange
    state = create_empty_state()
    state["nlu_result"] = {
        "message_type": "interruption",
        "command": "book_flight",
    }

    # Act
    next_node = route_after_understand(state)

    # Assert
    assert next_node == "handle_intent_change"


def test_route_after_understand_digression():
    """Test routing with digression message type."""
    # Arrange
    state = create_empty_state()
    state["nlu_result"] = {
        "message_type": "digression",
        "command": "what_time",
    }

    # Act
    next_node = route_after_understand(state)

    # Assert
    assert next_node == "handle_digression"


def test_route_after_understand_no_nlu_result():
    """Test routing when no NLU result exists."""
    # Arrange
    state = create_empty_state()
    state["nlu_result"] = None

    # Act
    next_node = route_after_understand(state)

    # Assert
    assert next_node == "generate_response"


def test_route_after_validate_all_slots_filled():
    """Test routing when ready for action."""
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
    state["conversation_state"] = "ready_for_action"

    # Act
    next_node = route_after_validate(state)

    # Assert
    assert next_node == "execute_action"


def test_route_after_validate_slots_missing():
    """Test routing when waiting for slot."""
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
    state["conversation_state"] = "waiting_for_slot"

    # Act
    next_node = route_after_validate(state)

    # Assert
    assert next_node == "collect_next_slot"


def test_route_after_validate_no_active_flow():
    """Test routing when no active flow exists."""
    # Arrange
    state = create_empty_state()
    state["flow_stack"] = []

    # Act
    next_node = route_after_validate(state)

    # Assert
    assert next_node == "generate_response"
