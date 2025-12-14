"""Tests for routing functions."""

import logging
from unittest.mock import MagicMock

import pytest

from soni.core.state import create_empty_state
from soni.dm.routing import (
    activate_flow_by_intent,
    create_branch_router,
    route_after_action,
    route_after_collect_next_slot,
    route_after_confirmation,
    route_after_correction,
    route_after_modification,
    route_after_understand,
    route_after_validate,
    route_by_intent,
    should_continue,
    should_continue_flow,
)


def test_route_after_understand_slot_value():
    """Test routing with slot_value message type."""
    # Arrange
    state = create_empty_state()
    # Add active flow so routing goes directly to validate_slot
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


def test_route_after_validate_warns_unexpected_state():
    """Test that route_after_validate handles unexpected conversation_state."""
    # Arrange
    state = create_empty_state()
    state["conversation_state"] = "unexpected_state"

    # Act
    result = route_after_validate(state)

    # Assert - Verify routing behavior
    assert result == "generate_response"


def test_route_after_understand_with_slot_value():
    """Test that route_after_understand routes slot_value to validate_slot."""
    # Arrange
    state = create_empty_state()
    # Add active flow so routing goes directly to validate_slot
    state["flow_stack"] = [
        {
            "flow_id": "flow_1",
            "flow_name": "test_flow",
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
        "message_type": "slot_value",
        "command": "test_command",
        "slots": [{"name": "test_slot"}],
        "confidence": 0.9,
    }

    # Act
    result = route_after_understand(state)

    # Assert - Verify routing behavior
    assert result == "validate_slot"


def test_route_after_understand_handles_unknown_message_type():
    """Test that route_after_understand handles unknown message_type."""
    # Arrange
    state = create_empty_state()
    state["nlu_result"] = {
        "message_type": "unknown_type",
        "command": "test_command",
    }

    # Act
    result = route_after_understand(state)

    # Assert - Verify routing behavior
    assert result == "generate_response"


def test_route_after_validate_ready_for_action():
    """Test that route_after_validate routes ready_for_action to execute_action."""
    # Arrange
    state = create_empty_state()
    state["conversation_state"] = "ready_for_action"

    # Act
    result = route_after_validate(state)

    # Assert - Verify routing behavior
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


# === TESTS FOR route_after_understand - ADDITIONAL CASES ===


@pytest.mark.parametrize(
    "message_type,expected_node,conversation_state",
    [
        ("slot_value", "validate_slot", "waiting_for_slot"),
        ("correction", "handle_correction", "waiting_for_slot"),
        ("modification", "handle_modification", "waiting_for_slot"),
        ("confirmation", "handle_confirmation", "confirming"),
        ("intent_change", "handle_intent_change", None),
        ("question", "handle_digression", None),
        ("clarification", "handle_clarification", None),  # Clarification has dedicated handler
        ("cancellation", "handle_cancellation", None),
    ],
)
def test_route_after_understand_message_types_parametrized(
    message_type, expected_node, conversation_state
):
    """Test routing for all message types (parametrized)."""
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
    if conversation_state:
        state["conversation_state"] = conversation_state

    # Use appropriate command based on message type
    # - For question/clarification: use None to avoid cross-flow rerouting
    # - For intent_change/cancellation: command is expected
    # - For other types: use same flow name to avoid rerouting
    command = None
    if message_type in ("intent_change", "cancellation"):
        command = "book_flight"  # Use current flow for non-cross-flow scenarios
    elif message_type in ("slot_value", "correction", "modification", "confirmation"):
        command = "book_flight"
    # else: command = None for question/clarification

    state["nlu_result"] = {
        "message_type": message_type,
        "command": command,
        "slots": [],
    }

    # Act
    result = route_after_understand(state)

    # Assert
    assert result == expected_node


def test_route_after_understand_slot_value_with_confirming_state():
    """Test that slot_value during confirming state routes to handle_confirmation."""
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
    state["conversation_state"] = "confirming"
    state["nlu_result"] = {
        "message_type": "slot_value",
        "command": "continue",
        "slots": [{"name": "origin", "value": "Madrid"}],
    }

    # Act
    result = route_after_understand(state)

    # Assert
    assert result == "handle_confirmation"


def test_route_after_understand_slot_value_understanding_with_existing_slot():
    """Test that slot_value in understanding state with existing slot routes to modification."""
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
    state["flow_slots"] = {"flow_1": {"destination": "Barcelona"}}
    state["conversation_state"] = "understanding"
    state["nlu_result"] = {
        "message_type": "slot_value",
        "command": "continue",
        "slots": [{"name": "destination", "value": "Valencia"}],
    }

    # Act
    result = route_after_understand(state)

    # Assert
    assert result == "handle_modification"


def test_route_after_understand_slot_value_no_flow_with_command():
    """Test that slot_value with no flow but command routes to handle_intent_change."""
    # Arrange
    state = create_empty_state()
    state["flow_stack"] = []
    state["nlu_result"] = {
        "message_type": "slot_value",
        "command": "book_flight",
        "slots": [{"name": "origin", "value": "Madrid"}],
    }

    # Act
    result = route_after_understand(state)

    # Assert
    assert result == "handle_intent_change"


def test_route_after_understand_correction_no_flow_with_command():
    """Test that correction with no flow but command routes to handle_intent_change."""
    # Arrange
    state = create_empty_state()
    state["flow_stack"] = []
    state["nlu_result"] = {
        "message_type": "correction",
        "command": "book_flight",
        "slots": [{"name": "destination", "value": "Barcelona"}],
    }

    # Act
    result = route_after_understand(state)

    # Assert
    assert result == "handle_intent_change"


def test_route_after_understand_modification_no_flow_with_command():
    """Test that modification with no flow but command routes to handle_intent_change."""
    # Arrange
    state = create_empty_state()
    state["flow_stack"] = []
    state["nlu_result"] = {
        "message_type": "modification",
        "command": "book_flight",
        "slots": [{"name": "destination", "value": "Valencia"}],
    }

    # Act
    result = route_after_understand(state)

    # Assert
    assert result == "handle_intent_change"


def test_route_after_understand_confirmation_not_in_confirming_state():
    """Test that confirmation not in confirming state routes based on flow."""
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
    state["nlu_result"] = {
        "message_type": "confirmation",
        "command": "continue",
    }

    # Act
    result = route_after_understand(state)

    # Assert - should route to collect_next_slot since has active flow
    assert result == "collect_next_slot"


def test_route_after_understand_confirmation_in_confirming_state():
    """Test that confirmation in confirming state routes to handle_confirmation."""
    # Arrange
    state = create_empty_state()
    state["conversation_state"] = "confirming"
    state["nlu_result"] = {
        "message_type": "confirmation",
        "command": "continue",
    }

    # Act
    result = route_after_understand(state)

    # Assert
    assert result == "handle_confirmation"


def test_route_after_understand_continuation_no_flow_no_command():
    """Test that continuation with no flow and no command routes to generate_response."""
    # Arrange
    state = create_empty_state()
    state["flow_stack"] = []
    state["nlu_result"] = {
        "message_type": "continuation",
        "command": None,
        "slots": [],
    }

    # Act
    result = route_after_understand(state)

    # Assert
    assert result == "generate_response"


def test_route_after_understand_message_type_enum():
    """Test that route_after_understand handles MessageType enum."""
    # Arrange
    from soni.du.models import MessageType

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
    # Use enum instead of string
    state["nlu_result"] = {
        "message_type": MessageType.SLOT_VALUE,
        "command": "continue",
        "slots": [],
    }

    # Act
    result = route_after_understand(state)

    # Assert
    assert result == "validate_slot"


# === TESTS FOR route_after_validate ===


def test_route_after_validate_ready_for_confirmation():
    """Test routing when ready for confirmation."""
    # Arrange
    state = create_empty_state()
    state["conversation_state"] = "ready_for_confirmation"

    # Act
    result = route_after_validate(state)

    # Assert
    assert result == "confirm_action"


def test_route_after_validate_completed():
    """Test routing when flow is completed."""
    # Arrange
    state = create_empty_state()
    state["conversation_state"] = "completed"

    # Act
    result = route_after_validate(state)

    # Assert
    assert result == "generate_response"


# === TESTS FOR route_after_correction ===


def test_route_after_correction_ready_for_action():
    """Test routing after correction when ready for action."""
    # Arrange
    state = create_empty_state()
    state["conversation_state"] = "ready_for_action"

    # Act
    result = route_after_correction(state)

    # Assert
    assert result == "execute_action"


def test_route_after_correction_ready_for_confirmation():
    """Test routing after correction when ready for confirmation."""
    # Arrange
    state = create_empty_state()
    state["conversation_state"] = "ready_for_confirmation"

    # Act
    result = route_after_correction(state)

    # Assert
    assert result == "confirm_action"


def test_route_after_correction_waiting_for_slot():
    """Test routing after correction when waiting for slot."""
    # Arrange
    state = create_empty_state()
    state["conversation_state"] = "waiting_for_slot"

    # Act
    result = route_after_correction(state)

    # Assert
    assert result == "collect_next_slot"


def test_route_after_correction_other_state():
    """Test routing after correction with other state."""
    # Arrange
    state = create_empty_state()
    state["conversation_state"] = "error"

    # Act
    result = route_after_correction(state)

    # Assert
    assert result == "generate_response"


# === TESTS FOR route_after_modification ===


def test_route_after_modification_ready_for_action():
    """Test routing after modification when ready for action."""
    # Arrange
    state = create_empty_state()
    state["conversation_state"] = "ready_for_action"

    # Act
    result = route_after_modification(state)

    # Assert
    assert result == "execute_action"


def test_route_after_modification_ready_for_confirmation():
    """Test routing after modification when ready for confirmation."""
    # Arrange
    state = create_empty_state()
    state["conversation_state"] = "ready_for_confirmation"

    # Act
    result = route_after_modification(state)

    # Assert
    assert result == "confirm_action"


def test_route_after_modification_waiting_for_slot():
    """Test routing after modification when waiting for slot."""
    # Arrange
    state = create_empty_state()
    state["conversation_state"] = "waiting_for_slot"

    # Act
    result = route_after_modification(state)

    # Assert
    assert result == "collect_next_slot"


def test_route_after_modification_other_state():
    """Test routing after modification with other state."""
    # Arrange
    state = create_empty_state()
    state["conversation_state"] = "error"

    # Act
    result = route_after_modification(state)

    # Assert
    assert result == "generate_response"


# === TESTS FOR route_after_collect_next_slot ===


def test_route_after_collect_next_slot_ready_for_action():
    """Test routing after collect_next_slot when ready for action."""
    # Arrange
    state = create_empty_state()
    state["conversation_state"] = "ready_for_action"

    # Act
    result = route_after_collect_next_slot(state)

    # Assert
    assert result == "execute_action"


def test_route_after_collect_next_slot_ready_for_confirmation():
    """Test routing after collect_next_slot when ready for confirmation."""
    # Arrange
    state = create_empty_state()
    state["conversation_state"] = "ready_for_confirmation"

    # Act
    result = route_after_collect_next_slot(state)

    # Assert
    assert result == "confirm_action"


def test_route_after_collect_next_slot_waiting_for_slot_with_message():
    """Test routing after collect_next_slot when waiting for slot with user message."""
    # Arrange
    state = create_empty_state()
    state["conversation_state"] = "waiting_for_slot"
    state["user_message"] = "Madrid"

    # Act
    result = route_after_collect_next_slot(state)

    # Assert
    assert result == "understand"


def test_route_after_collect_next_slot_waiting_for_slot_no_message():
    """Test routing after collect_next_slot when waiting for slot without user message."""
    # Arrange
    state = create_empty_state()
    state["conversation_state"] = "waiting_for_slot"
    state["user_message"] = ""

    # Act
    result = route_after_collect_next_slot(state)

    # Assert
    assert result == "generate_response"


def test_route_after_collect_next_slot_completed():
    """Test routing after collect_next_slot when completed."""
    # Arrange
    state = create_empty_state()
    state["conversation_state"] = "completed"

    # Act
    result = route_after_collect_next_slot(state)

    # Assert
    assert result == "generate_response"


def test_route_after_collect_next_slot_generating_response():
    """Test routing after collect_next_slot when generating response."""
    # Arrange
    state = create_empty_state()
    state["conversation_state"] = "generating_response"

    # Act
    result = route_after_collect_next_slot(state)

    # Assert
    assert result == "generate_response"


def test_route_after_collect_next_slot_other_state_with_message():
    """Test routing after collect_next_slot with other state but has user message."""
    # Arrange
    state = create_empty_state()
    state["conversation_state"] = "error"
    state["user_message"] = "test message"

    # Act
    result = route_after_collect_next_slot(state)

    # Assert
    assert result == "understand"


def test_route_after_collect_next_slot_other_state_no_message():
    """Test routing after collect_next_slot with other state and no user message."""
    # Arrange
    state = create_empty_state()
    state["conversation_state"] = "error"
    state["user_message"] = ""

    # Act
    result = route_after_collect_next_slot(state)

    # Assert
    assert result == "generate_response"


# === TESTS FOR route_after_action ===


def test_route_after_action_ready_for_action():
    """Test routing after action when ready for another action."""
    # Arrange
    state = create_empty_state()
    state["conversation_state"] = "ready_for_action"

    # Act
    result = route_after_action(state)

    # Assert
    assert result == "execute_action"


def test_route_after_action_ready_for_confirmation():
    """Test routing after action when ready for confirmation."""
    # Arrange
    state = create_empty_state()
    state["conversation_state"] = "ready_for_confirmation"

    # Act
    result = route_after_action(state)

    # Assert
    assert result == "confirm_action"


def test_route_after_action_completed():
    """Test routing after action when flow is completed."""
    # Arrange
    state = create_empty_state()
    state["conversation_state"] = "completed"

    # Act
    result = route_after_action(state)

    # Assert
    assert result == "generate_response"


def test_route_after_action_generating_response():
    """Test routing after action when generating response."""
    # Arrange
    state = create_empty_state()
    state["conversation_state"] = "generating_response"

    # Act
    result = route_after_action(state)

    # Assert
    assert result == "generate_response"


def test_route_after_action_waiting_for_slot():
    """Test routing after action when waiting for slot (unexpected)."""
    # Arrange
    state = create_empty_state()
    state["conversation_state"] = "waiting_for_slot"

    # Act
    result = route_after_action(state)

    # Assert
    assert result == "generate_response"


def test_route_after_action_other_state():
    """Test routing after action with other state."""
    # Arrange
    state = create_empty_state()
    state["conversation_state"] = "error"

    # Act
    result = route_after_action(state)

    # Assert
    assert result == "generate_response"


# === TESTS FOR route_after_confirmation ===


def test_route_after_confirmation_ready_for_action():
    """Test routing after confirmation when ready for action (user confirmed)."""
    # Arrange
    state = create_empty_state()
    state["conversation_state"] = "ready_for_action"

    # Act
    result = route_after_confirmation(state)

    # Assert
    assert result == "execute_action"


def test_route_after_confirmation_confirming():
    """Test routing after confirmation when still confirming (unclear)."""
    # Arrange
    state = create_empty_state()
    state["conversation_state"] = "confirming"

    # Act
    result = route_after_confirmation(state)

    # Assert
    assert result == "generate_response"


def test_route_after_confirmation_error():
    """Test routing after confirmation when error."""
    # Arrange
    state = create_empty_state()
    state["conversation_state"] = "error"

    # Act
    result = route_after_confirmation(state)

    # Assert
    assert result == "generate_response"


def test_route_after_confirmation_understanding():
    """Test routing after confirmation when understanding (user denied)."""
    # Arrange
    state = create_empty_state()
    state["conversation_state"] = "understanding"

    # Act
    result = route_after_confirmation(state)

    # Assert
    assert result == "generate_response"


def test_route_after_confirmation_other_state():
    """Test routing after confirmation with other state."""
    # Arrange
    state = create_empty_state()
    state["conversation_state"] = "waiting_for_slot"

    # Act
    result = route_after_confirmation(state)

    # Assert
    assert result == "generate_response"


# === TESTS FOR should_continue_flow ===


def test_should_continue_flow_no_trace():
    """Test should_continue_flow with no trace."""
    # Arrange
    state = create_empty_state()
    state["trace"] = []

    # Act
    result = should_continue_flow(state)

    # Assert
    assert result == "next"


def test_should_continue_flow_slot_collection_event():
    """Test should_continue_flow with slot collection event."""
    # Arrange
    from soni.core.events import EVENT_SLOT_COLLECTION

    state = create_empty_state()
    state["trace"] = [{"event": EVENT_SLOT_COLLECTION}]

    # Act
    result = should_continue_flow(state)

    # Assert
    assert result == "end"


def test_should_continue_flow_validation_error_event():
    """Test should_continue_flow with validation error event."""
    # Arrange
    from soni.core.events import EVENT_VALIDATION_ERROR

    state = create_empty_state()
    state["trace"] = [{"event": EVENT_VALIDATION_ERROR}]

    # Act
    result = should_continue_flow(state)

    # Assert
    assert result == "end"


def test_should_continue_flow_other_event():
    """Test should_continue_flow with other event."""
    # Arrange
    state = create_empty_state()
    state["trace"] = [{"event": "other_event"}]

    # Act
    result = should_continue_flow(state)

    # Assert
    assert result == "next"


# === TESTS FOR activate_flow_by_intent ===


def test_activate_flow_by_intent_exact_match():
    """Test activate_flow_by_intent with exact match."""
    # Arrange
    config = MagicMock()
    config.flows = {"book_flight": MagicMock(), "book_hotel": MagicMock()}

    # Act
    result = activate_flow_by_intent("book_flight", "current_flow", config)

    # Assert
    assert result == "book_flight"


def test_activate_flow_by_intent_normalized_match():
    """Test activate_flow_by_intent with normalized match."""
    # Arrange
    config = MagicMock()
    config.flows = {"book_flight": MagicMock()}

    # Act
    result = activate_flow_by_intent("book-flight", "current_flow", config)

    # Assert
    assert result == "book_flight"


def test_activate_flow_by_intent_no_match():
    """Test activate_flow_by_intent with no match."""
    # Arrange
    config = MagicMock()
    config.flows = {"book_flight": MagicMock()}

    # Act
    result = activate_flow_by_intent("unknown_flow", "current_flow", config)

    # Assert
    assert result == "current_flow"


def test_activate_flow_by_intent_no_command():
    """Test activate_flow_by_intent with no command."""
    # Arrange
    config = MagicMock()
    config.flows = {"book_flight": MagicMock()}

    # Act
    result = activate_flow_by_intent(None, "current_flow", config)

    # Assert
    assert result == "current_flow"


def test_activate_flow_by_intent_no_flows_attr():
    """Test activate_flow_by_intent when config has no flows attribute."""
    # Arrange
    config = MagicMock()
    del config.flows

    # Act
    result = activate_flow_by_intent("book_flight", "current_flow", config)

    # Assert
    assert result == "current_flow"


# === TESTS FOR create_branch_router ===


def test_create_branch_router_success():
    """Test create_branch_router with valid case."""
    # Arrange
    state = create_empty_state()
    state["flow_stack"] = [
        {
            "flow_id": "flow_1",
            "flow_name": "test_flow",
            "flow_state": "active",
            "current_step": None,
            "outputs": {},
            "started_at": 0.0,
            "paused_at": None,
            "completed_at": None,
            "context": None,
        }
    ]
    state["flow_slots"] = {"flow_1": {"status": "ok"}}

    router = create_branch_router("status", {"ok": "continue", "error": "handle_error"})

    # Act
    result = router(state)

    # Assert
    assert result == "continue"


def test_create_branch_router_value_not_found():
    """Test create_branch_router when value not found in cases."""
    # Arrange
    state = create_empty_state()
    state["flow_stack"] = [
        {
            "flow_id": "flow_1",
            "flow_name": "test_flow",
            "flow_state": "active",
            "current_step": None,
            "outputs": {},
            "started_at": 0.0,
            "paused_at": None,
            "completed_at": None,
            "context": None,
        }
    ]
    state["flow_slots"] = {"flow_1": {"status": "unknown"}}

    router = create_branch_router("status", {"ok": "continue", "error": "handle_error"})

    # Act & Assert
    with pytest.raises(ValueError, match="value 'unknown' not found in cases"):
        router(state)


def test_create_branch_router_variable_not_found():
    """Test create_branch_router when variable not found in state."""
    # Arrange
    state = create_empty_state()
    state["flow_stack"] = [
        {
            "flow_id": "flow_1",
            "flow_name": "test_flow",
            "flow_state": "active",
            "current_step": None,
            "outputs": {},
            "started_at": 0.0,
            "paused_at": None,
            "completed_at": None,
            "context": None,
        }
    ]
    state["flow_slots"] = {"flow_1": {}}

    router = create_branch_router("status", {"ok": "continue"})

    # Act & Assert
    with pytest.raises(ValueError, match="input variable 'status' not found"):
        router(state)


def test_create_branch_router_converts_value_to_string():
    """Test that create_branch_router converts value to string for comparison."""
    # Arrange
    state = create_empty_state()
    state["flow_stack"] = [
        {
            "flow_id": "flow_1",
            "flow_name": "test_flow",
            "flow_state": "active",
            "current_step": None,
            "outputs": {},
            "started_at": 0.0,
            "paused_at": None,
            "completed_at": None,
            "context": None,
        }
    ]
    state["flow_slots"] = {"flow_1": {"count": 5}}  # Integer value

    router = create_branch_router("count", {"5": "continue", "10": "stop"})

    # Act
    result = router(state)

    # Assert
    assert result == "continue"


# === TESTS FOR should_continue and route_by_intent (placeholders) ===


def test_should_continue():
    """Test should_continue placeholder function."""
    # Arrange
    state = create_empty_state()

    # Act
    result = should_continue(state)

    # Assert
    assert result == "continue"


def test_route_by_intent():
    """Test route_by_intent placeholder function."""
    # Arrange
    state = create_empty_state()

    # Act
    result = route_by_intent(state)

    # Assert
    assert result == "fallback"
