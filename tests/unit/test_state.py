"""Unit tests for state initialization helpers."""

import pytest

from soni.core.state import create_empty_state, create_initial_state
from soni.core.types import DialogueState


def test_create_empty_state():
    """Test create_empty_state returns valid state."""
    # Arrange
    # (No setup needed)

    # Act
    state = create_empty_state()

    # Assert
    assert state["conversation_state"] == "idle"
    assert state["turn_count"] == 0
    assert len(state["flow_stack"]) == 0
    assert state["user_message"] == ""
    assert state["last_response"] == ""
    assert len(state["messages"]) == 0
    assert len(state["flow_slots"]) == 0
    assert state["nlu_result"] is None
    assert state["last_nlu_call"] is None
    assert state["digression_depth"] == 0
    assert state["last_digression_type"] is None
    assert len(state["trace"]) == 0
    assert isinstance(state["metadata"], dict)


def test_create_initial_state():
    """Test create_initial_state with message."""
    # Arrange
    user_message = "Hello"

    # Act
    state = create_initial_state(user_message)

    # Assert
    assert state["user_message"] == "Hello"
    assert state["conversation_state"] == "understanding"
    assert state["turn_count"] == 1
    assert len(state["trace"]) == 1
    assert state["trace"][0]["user_message"] == "Hello"
    assert state["trace"][0]["turn"] == 1
    assert "timestamp" in state["trace"][0]


def test_create_initial_state_uses_empty_state():
    """Test create_initial_state builds on create_empty_state."""
    # Arrange
    test_message = "Test message"

    # Act
    state = create_initial_state(test_message)

    # Assert - verify it has all fields from empty_state
    assert "flow_stack" in state
    assert "flow_slots" in state
    assert "messages" in state
    # And has overridden values
    assert state["user_message"] == test_message
    assert state["conversation_state"] == "understanding"
    assert state["turn_count"] == 1
