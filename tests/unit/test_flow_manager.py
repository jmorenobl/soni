"""Unit tests for FlowManager."""

import pytest

from soni.core.errors import FlowStackLimitError
from soni.core.types import DialogueState
from soni.flow.manager import FlowManager


@pytest.fixture
def empty_state() -> DialogueState:
    """Create empty dialogue state."""
    return {
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


def test_push_flow_creates_instance(empty_state):
    """Test push_flow creates new flow instance."""
    # Arrange
    manager = FlowManager()

    # Act
    flow_id = manager.push_flow(empty_state, "book_flight")

    # Assert
    assert len(empty_state["flow_stack"]) == 1
    assert empty_state["flow_stack"][0]["flow_name"] == "book_flight"
    assert empty_state["flow_stack"][0]["flow_state"] == "active"
    assert flow_id in empty_state["flow_slots"]


def test_pop_flow_archives_completed(empty_state):
    """Test pop_flow archives completed flow."""
    # Arrange
    manager = FlowManager()
    manager.push_flow(empty_state, "book_flight")

    # Act
    manager.pop_flow(empty_state, outputs={"booking_ref": "BK-123"})

    # Assert
    assert len(empty_state["flow_stack"]) == 0
    assert len(empty_state["metadata"]["completed_flows"]) == 1
    assert empty_state["metadata"]["completed_flows"][0]["outputs"]["booking_ref"] == "BK-123"


def test_nested_flows_pause_resume(empty_state):
    """Test nested flows pause and resume correctly."""
    # Arrange
    manager = FlowManager()

    # Act
    manager.push_flow(empty_state, "flow_1")
    assert empty_state["flow_stack"][0]["flow_state"] == "active"

    manager.push_flow(empty_state, "flow_2")

    # Assert
    assert empty_state["flow_stack"][0]["flow_state"] == "paused"
    assert empty_state["flow_stack"][1]["flow_state"] == "active"

    # Act - Pop flow_2
    manager.pop_flow(empty_state)

    # Assert - flow_1 resumed
    assert empty_state["flow_stack"][0]["flow_state"] == "active"


def test_get_set_slot(empty_state):
    """Test get_slot and set_slot operations."""
    # Arrange
    manager = FlowManager()
    manager.push_flow(empty_state, "book_flight")

    # Act
    manager.set_slot(empty_state, "origin", "NYC")
    value = manager.get_slot(empty_state, "origin")

    # Assert
    assert value == "NYC"


def test_stack_depth_limit(empty_state):
    """Test stack depth limit enforcement."""
    # Arrange
    manager = FlowManager(max_stack_depth=2)

    # Act
    manager.push_flow(empty_state, "flow_1")
    manager.push_flow(empty_state, "flow_2")

    # Assert
    with pytest.raises(FlowStackLimitError):
        manager.push_flow(empty_state, "flow_3")


def test_get_active_context(empty_state):
    """Test get_active_context returns current flow."""
    # Arrange
    manager = FlowManager()

    # Act
    context_before = manager.get_active_context(empty_state)
    flow_id = manager.push_flow(empty_state, "book_flight")
    context_after = manager.get_active_context(empty_state)

    # Assert
    assert context_before is None
    assert context_after is not None
    assert context_after["flow_id"] == flow_id
    assert context_after["flow_name"] == "book_flight"


def test_pop_flow_with_no_stack(empty_state):
    """Test pop_flow handles empty stack gracefully."""
    # Arrange
    manager = FlowManager()

    # Act
    manager.pop_flow(empty_state)

    # Assert
    assert len(empty_state["flow_stack"]) == 0


def test_push_flow_with_inputs(empty_state):
    """Test push_flow initializes flow_slots with inputs."""
    # Arrange
    manager = FlowManager()
    inputs = {"booking_ref": "BK-123", "status": "confirmed"}

    # Act
    flow_id = manager.push_flow(empty_state, "modify_booking", inputs=inputs)

    # Assert
    assert empty_state["flow_slots"][flow_id]["booking_ref"] == "BK-123"
    assert empty_state["flow_slots"][flow_id]["status"] == "confirmed"


def test_prune_state_removes_orphan_slots(empty_state):
    """Test prune_state removes orphaned flow_slots."""
    # Arrange
    manager = FlowManager()

    # Create and complete a flow (should leave orphan slot)
    manager.push_flow(empty_state, "test_flow")
    manager.pop_flow(empty_state)

    # Manually add orphan slot
    empty_state["flow_slots"]["orphan_123"] = {"data": "test"}

    # Act
    manager.prune_state(empty_state)

    # Assert
    assert "orphan_123" not in empty_state["flow_slots"]


def test_prune_state_limits_completed_flows(empty_state):
    """Test prune_state limits completed flows."""
    # Arrange
    manager = FlowManager()

    # Create many completed flows
    for i in range(15):
        manager.push_flow(empty_state, f"flow_{i}")
        manager.pop_flow(empty_state)

    # Act
    manager.prune_state(empty_state, max_completed_flows=10)

    # Assert
    assert len(empty_state["metadata"]["completed_flows"]) == 10


def test_prune_state_limits_trace(empty_state):
    """Test prune_state limits trace entries."""
    # Arrange
    manager = FlowManager()

    # Add many trace entries
    for i in range(60):
        empty_state["trace"].append({"event": f"event_{i}", "turn": i})

    # Act
    manager.prune_state(empty_state, max_trace=50)

    # Assert
    assert len(empty_state["trace"]) == 50
    assert empty_state["trace"][0]["event"] == "event_10"  # First kept entry


def test_prune_state_keeps_active_slots(empty_state):
    """Test prune_state keeps slots for active flows."""
    # Arrange
    manager = FlowManager()
    flow_id = manager.push_flow(empty_state, "active_flow")
    manager.set_slot(empty_state, "test_slot", "value")

    # Add orphan slot
    empty_state["flow_slots"]["orphan_123"] = {"data": "test"}

    # Act
    manager.prune_state(empty_state)

    # Assert
    assert flow_id in empty_state["flow_slots"]
    assert empty_state["flow_slots"][flow_id]["test_slot"] == "value"
    assert "orphan_123" not in empty_state["flow_slots"]
