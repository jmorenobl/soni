"""Unit tests for core type definitions."""

import pytest

from soni.core.types import (
    ConversationState,
    DialogueState,
    FlowContext,
    FlowState,
    RuntimeContext,
)


def test_flow_context_structure():
    """Test FlowContext has all required fields."""
    # Arrange
    context: FlowContext = {
        "flow_id": "test_123",
        "flow_name": "test_flow",
        "flow_state": "active",
        "current_step": None,
        "outputs": {},
        "started_at": 1234567890.0,
        "paused_at": None,
        "completed_at": None,
        "context": None,
    }

    # Act
    # (TypedDict access is the "act")

    # Assert
    assert context["flow_id"] == "test_123"
    assert context["flow_state"] == "active"
    assert context["flow_name"] == "test_flow"
    assert context["current_step"] is None
    assert isinstance(context["outputs"], dict)
    assert context["started_at"] == 1234567890.0


def test_dialogue_state_initialization():
    """Test DialogueState can be initialized with defaults."""
    # Arrange & Act
    state: DialogueState = {
        "user_message": "",
        "last_response": "",
        "messages": [],
        "flow_stack": [],
        "flow_slots": {},
        "conversation_state": "idle",
        "current_step": None,
        "waiting_for_slot": None,
        "nlu_result": None,
        "last_nlu_call": None,
        "digression_depth": 0,
        "last_digression_type": None,
        "turn_count": 0,
        "trace": [],
        "metadata": {},
    }

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


def test_flow_state_literal():
    """Test FlowState literal values are valid."""
    # Arrange
    valid_states: list[FlowState] = [
        "active",
        "paused",
        "completed",
        "cancelled",
        "abandoned",
        "error",
    ]

    # Act
    # (Type checking validates literals)

    # Assert
    assert len(valid_states) == 6
    assert "active" in valid_states
    assert "paused" in valid_states
    assert "completed" in valid_states
    assert "cancelled" in valid_states
    assert "abandoned" in valid_states
    assert "error" in valid_states


def test_conversation_state_literal():
    """Test ConversationState literal values are valid."""
    # Arrange
    valid_states: list[ConversationState] = [
        "idle",
        "understanding",
        "waiting_for_slot",
        "validating_slot",
        "collecting",
        "executing_action",
        "generating_response",
        "error",
    ]

    # Act
    # (Type checking validates literals)

    # Assert
    assert len(valid_states) == 8
    assert "idle" in valid_states
    assert "understanding" in valid_states
    assert "waiting_for_slot" in valid_states
    assert "validating_slot" in valid_states
    assert "collecting" in valid_states
    assert "executing_action" in valid_states
    assert "generating_response" in valid_states
    assert "error" in valid_states


def test_runtime_context_structure():
    """Test RuntimeContext has all required fields."""
    # Arrange
    context: RuntimeContext = {
        "flow_manager": None,
        "nlu_provider": None,
        "action_handler": None,
        "scope_manager": None,
        "normalizer": None,
    }

    # Act
    # (TypedDict access is the "act")

    # Assert
    assert "flow_manager" in context
    assert "nlu_provider" in context
    assert "action_handler" in context
    assert "scope_manager" in context
    assert "normalizer" in context
