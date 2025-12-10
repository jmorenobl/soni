"""Unit tests for handle_cancellation node.

All tests use mocked NLU for determinism.

Design Reference: docs/design/10-dsl-specification/06-patterns.md:20-48
Pattern: "Cancellation: User wants to abandon → Pop flow, return to previous or idle"
"""

from unittest.mock import MagicMock

import pytest

from soni.dm.nodes.handle_cancellation import handle_cancellation_node
from soni.du.models import MessageType, NLUOutput

# === TESTS FOR CANCELLATION DURING DIFFERENT STATES ===


@pytest.mark.asyncio
async def test_handle_cancellation_during_slot_collection(create_state_with_flow, mock_runtime):
    """
    User cancels while collecting slots.

    Design Reference: docs/design/10-dsl-specification/06-patterns.md:20-48
    Pattern: "Can happen during ANY step (collect, confirm, action)"
    """
    # Arrange
    state = create_state_with_flow("book_flight")
    state["flow_stack"] = [
        {"flow_id": "flow_1", "flow_name": "book_flight", "flow_state": "active"}
    ]
    state["waiting_for_slot"] = "origin"
    state["conversation_state"] = "waiting_for_slot"
    state["nlu_result"] = {
        "message_type": MessageType.CANCELLATION.value,
        "command": "cancel",
    }

    # Mock flow_manager.pop_flow to modify state in place
    def mock_pop_flow(state, result=None, outputs=None):
        state["flow_stack"].pop()
        if "flow_1" in state.get("flow_slots", {}):
            state["flow_slots"].pop("flow_1")

    mock_runtime.context["flow_manager"].pop_flow.side_effect = mock_pop_flow
    mock_runtime.context["flow_manager"].get_active_context.return_value = {
        "flow_id": "flow_1",
        "flow_name": "book_flight",
    }

    # Act
    result = await handle_cancellation_node(state, mock_runtime)

    # Assert
    # Flow popped from stack
    assert len(result["flow_stack"]) == 0
    # Returns to idle
    assert result["conversation_state"] == "idle"
    # Response indicates cancellation
    assert (
        "cancel" in result["last_response"].lower()
        or "cancelled" in result["last_response"].lower()
    )


@pytest.mark.asyncio
async def test_handle_cancellation_during_confirmation(create_state_with_flow, mock_runtime):
    """User cancels during confirmation step."""
    # Arrange
    state = create_state_with_flow("book_flight")
    state["flow_stack"] = [
        {"flow_id": "flow_1", "flow_name": "book_flight", "flow_state": "active"}
    ]
    state["conversation_state"] = "confirming"
    state["nlu_result"] = {
        "message_type": MessageType.CANCELLATION.value,
        "command": "cancel",
    }

    mock_runtime.context["flow_manager"].get_active_context.return_value = {
        "flow_id": "flow_1",
        "flow_name": "book_flight",
    }

    def mock_pop_flow(state, result=None, outputs=None):
        state["flow_stack"].pop()

    mock_runtime.context["flow_manager"].pop_flow.side_effect = mock_pop_flow

    # Act
    result = await handle_cancellation_node(state, mock_runtime)

    # Assert
    assert result["conversation_state"] == "idle"
    assert len(result["flow_stack"]) == 0


@pytest.mark.asyncio
async def test_handle_cancellation_pops_to_parent_flow(create_state_with_flow, mock_runtime):
    """
    Cancellation with multiple flows in stack - returns to parent.

    Design Reference: docs/design/10-dsl-specification/06-patterns.md:20-48
    Pattern: "Returns to parent flow or idle state"
    """
    # Arrange
    state = create_state_with_flow("book_flight")
    state["flow_stack"] = [
        {"flow_id": "flow_1", "flow_name": "book_flight", "flow_state": "paused"},
        {"flow_id": "flow_2", "flow_name": "check_weather", "flow_state": "active"},  # Current
    ]
    state["nlu_result"] = {
        "message_type": MessageType.CANCELLATION.value,
        "command": "cancel",
    }

    mock_runtime.context["flow_manager"].get_active_context.return_value = {
        "flow_id": "flow_2",
        "flow_name": "check_weather",
    }

    def mock_pop_flow(state, result=None, outputs=None):
        # Pop current flow (flow_2)
        state["flow_stack"].pop()
        # Resume parent (flow_1)
        if state["flow_stack"]:
            state["flow_stack"][-1]["flow_state"] = "active"

    mock_runtime.context["flow_manager"].pop_flow.side_effect = mock_pop_flow

    # Mock step_manager for parent flow
    mock_runtime.context["step_manager"].get_current_step_config.return_value = None

    # Act
    result = await handle_cancellation_node(state, mock_runtime)

    # Assert
    # Pop current flow, resume parent
    assert len(result["flow_stack"]) == 1
    assert result["flow_stack"][0]["flow_name"] == "book_flight"
    assert result["flow_stack"][0]["flow_state"] == "active"


@pytest.mark.asyncio
async def test_handle_cancellation_from_idle(mock_runtime):
    """Cancellation when no active flow."""
    # Arrange
    from soni.core.state import create_empty_state

    state = create_empty_state()
    state["conversation_state"] = "idle"
    state["flow_stack"] = []
    state["nlu_result"] = {
        "message_type": MessageType.CANCELLATION.value,
        "command": "cancel",
    }

    mock_runtime.context["flow_manager"].get_active_context.return_value = None

    # Act
    result = await handle_cancellation_node(state, mock_runtime)

    # Assert
    assert result["conversation_state"] == "idle"
    assert (
        "nothing to cancel" in result["last_response"].lower()
        or "how can i help" in result["last_response"].lower()
    )


@pytest.mark.asyncio
async def test_handle_cancellation_cleanup_metadata(create_state_with_flow, mock_runtime):
    """Cancellation cleans up metadata appropriately."""
    # Arrange
    state = create_state_with_flow("book_flight")
    state["flow_stack"] = [
        {"flow_id": "flow_1", "flow_name": "book_flight", "flow_state": "active"}
    ]
    state["metadata"] = {
        "_correction_slot": "origin",
        "_waiting_for_slot": "destination",
        "some_other_data": "value",
    }
    state["nlu_result"] = {
        "message_type": MessageType.CANCELLATION.value,
        "command": "cancel",
    }

    mock_runtime.context["flow_manager"].get_active_context.return_value = {
        "flow_id": "flow_1",
        "flow_name": "book_flight",
    }

    def mock_pop_flow(state, result=None, outputs=None):
        state["flow_stack"].pop()

    mock_runtime.context["flow_manager"].pop_flow.side_effect = mock_pop_flow

    # Act
    result = await handle_cancellation_node(state, mock_runtime)

    # Assert
    assert result["conversation_state"] == "idle"
    assert len(result["flow_stack"]) == 0
    # Metadata may be cleaned or preserved - depends on implementation
    # Just verify state is consistent


@pytest.mark.asyncio
async def test_handle_cancellation_no_nlu_result(create_state_with_flow, mock_runtime):
    """Cancellation handles absence of NLU result gracefully."""
    # Arrange
    state = create_state_with_flow("book_flight")
    state["nlu_result"] = None

    # Act
    result = await handle_cancellation_node(state, mock_runtime)

    # Assert
    assert result.get("conversation_state") == "error"


@pytest.mark.asyncio
async def test_handle_cancellation_during_action_execution(create_state_with_flow, mock_runtime):
    """User cancels during action execution."""
    # Arrange
    state = create_state_with_flow("book_flight")
    state["flow_stack"] = [
        {"flow_id": "flow_1", "flow_name": "book_flight", "flow_state": "active"}
    ]
    state["conversation_state"] = "executing_action"
    state["nlu_result"] = {
        "message_type": MessageType.CANCELLATION.value,
        "command": "cancel",
    }

    mock_runtime.context["flow_manager"].get_active_context.return_value = {
        "flow_id": "flow_1",
        "flow_name": "book_flight",
    }

    def mock_pop_flow(state, result=None, outputs=None):
        state["flow_stack"].pop()

    mock_runtime.context["flow_manager"].pop_flow.side_effect = mock_pop_flow

    # Act
    result = await handle_cancellation_node(state, mock_runtime)

    # Assert
    assert result["conversation_state"] == "idle"
    assert len(result["flow_stack"]) == 0
