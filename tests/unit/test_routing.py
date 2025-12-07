"""Tests for routing functions."""

import logging

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


def test_route_after_validate_warns_unexpected_state(caplog):
    """Test that route_after_validate warns on unexpected conversation_state."""
    # Arrange
    from soni.dm.routing import logger as routing_logger

    state = create_empty_state()
    state["conversation_state"] = "unexpected_state"

    # Act
    with caplog.at_level(logging.WARNING, logger=routing_logger.name):
        result = route_after_validate(state)

    # Assert
    assert "Unexpected conversation_state" in caplog.text
    assert "unexpected_state" in caplog.text
    assert result == "generate_response"


def test_route_after_understand_logs_message_type(caplog):
    """Test that route_after_understand logs message_type correctly."""
    # Arrange
    from soni.dm.routing import logger as routing_logger

    state = create_empty_state()
    state["nlu_result"] = {
        "message_type": "slot_value",
        "command": "test_command",
        "slots": [{"name": "test_slot"}],
        "confidence": 0.9,
    }

    # Act
    with caplog.at_level(logging.INFO, logger=routing_logger.name):
        result = route_after_understand(state)

    # Assert
    assert "route_after_understand" in caplog.text
    assert "message_type=slot_value" in caplog.text
    assert "command=test_command" in caplog.text
    assert result == "validate_slot"


def test_route_after_understand_warns_unknown_message_type(caplog):
    """Test that route_after_understand warns on unknown message_type."""
    # Arrange
    from soni.dm.routing import logger as routing_logger

    state = create_empty_state()
    state["nlu_result"] = {
        "message_type": "unknown_type",
        "command": "test_command",
    }

    # Act
    with caplog.at_level(logging.WARNING, logger=routing_logger.name):
        result = route_after_understand(state)

    # Assert
    assert "Unknown message_type" in caplog.text
    assert "unknown_type" in caplog.text
    assert result == "generate_response"


def test_route_after_validate_logs_conversation_state(caplog):
    """Test that route_after_validate logs conversation_state."""
    # Arrange
    from soni.dm.routing import logger as routing_logger

    state = create_empty_state()
    state["conversation_state"] = "ready_for_action"

    # Act
    with caplog.at_level(logging.INFO, logger=routing_logger.name):
        result = route_after_validate(state)

    # Assert
    assert "route_after_validate" in caplog.text
    assert "conversation_state=ready_for_action" in caplog.text
    assert result == "execute_action"


def test_route_after_understand_continuation_no_flow_with_command():
    """Test that continuation with no active flow but command triggers intent_change."""
    # Arrange
    state = create_empty_state()
    state["flow_stack"] = []  # No active flow
    state["nlu_result"] = {
        "message_type": "continuation",
        "command": "book_flight",
        "slots": [],
    }

    # Act
    next_node = route_after_understand(state)

    # Assert - should treat as intent_change since there's a command but no active flow
    assert next_node == "handle_intent_change"


def test_route_after_understand_continuation_with_active_flow():
    """Test that continuation with active flow goes to collect_next_slot."""
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
    state["nlu_result"] = {
        "message_type": "continuation",
        "command": "book_flight",
        "slots": [],
    }

    # Act
    next_node = route_after_understand(state)

    # Assert - should continue with current flow
    assert next_node == "collect_next_slot"
