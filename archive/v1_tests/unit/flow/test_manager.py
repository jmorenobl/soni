"""Unit tests for FlowManager.

Tests for the immutable FlowManager that returns FlowDelta objects.
All mutation methods are now synchronous and return deltas.
"""

from typing import Any

import pytest

from soni.core.errors import FlowStackError
from soni.core.state import create_empty_dialogue_state
from soni.core.types import FlowContextState
from soni.flow.manager import FlowDelta, FlowManager, merge_delta


def apply_delta(state, delta):
    """Helper to apply delta to state for testing."""
    if delta is None:
        return
    if delta.flow_stack is not None:
        state["flow_stack"] = delta.flow_stack
    if delta.flow_slots is not None:
        state["flow_slots"] = delta.flow_slots


class TestFlowManagerPushFlow:
    """Tests for pushing flows onto the stack."""

    def test_push_flow_creates_context_on_empty_stack(self):
        """
        GIVEN an empty stack
        WHEN pushing a flow
        THEN returns flow_id and delta with updated stack
        """
        # Arrange
        state = create_empty_dialogue_state()
        manager = FlowManager()

        # Act
        flow_id, delta = manager.push_flow(state, "book_flight")
        apply_delta(state, delta)

        # Assert
        assert len(state["flow_stack"]) == 1
        assert state["flow_stack"][0]["flow_name"] == "book_flight"
        assert state["flow_stack"][0]["flow_id"] == flow_id
        assert flow_id in state["flow_slots"]

    def test_push_flow_with_inputs_stores_slots(self):
        """
        GIVEN inputs
        WHEN pushing a flow
        THEN inputs are stored in flow slots
        """
        # Arrange
        state = create_empty_dialogue_state()
        manager = FlowManager()

        # Act
        flow_id, delta = manager.push_flow(state, "book_flight", inputs={"origin": "NYC"})
        apply_delta(state, delta)

        # Assert
        assert state["flow_slots"][flow_id]["origin"] == "NYC"
        assert manager.get_slot(state, "origin") == "NYC"

    def test_push_flow_returns_flow_delta(self):
        """
        GIVEN empty state
        WHEN pushing a flow
        THEN returns FlowDelta with flow_stack and flow_slots
        """
        # Arrange
        state = create_empty_dialogue_state()
        manager = FlowManager()

        # Act
        flow_id, delta = manager.push_flow(state, "test_flow")

        # Assert
        assert isinstance(delta, FlowDelta)
        assert delta.flow_stack is not None
        assert delta.flow_slots is not None
        assert len(delta.flow_stack) == 1
        assert flow_id in delta.flow_slots


class TestFlowManagerPopFlow:
    """Tests for popping flows from the stack."""

    def test_pop_flow_on_empty_stack_raises_error(self):
        """
        GIVEN empty stack
        WHEN pop_flow is called
        THEN raises FlowStackError
        """
        # Arrange
        state = create_empty_dialogue_state()
        manager = FlowManager()

        # Act & Assert
        with pytest.raises(FlowStackError):
            manager.pop_flow(state)

    def test_pop_flow_returns_context_and_delta(self):
        """
        GIVEN stack with 1 flow
        WHEN pop_flow is called
        THEN returns (popped_context, delta)
        """
        # Arrange
        state = create_empty_dialogue_state()
        manager = FlowManager()
        _, push_delta = manager.push_flow(state, "flow1")
        apply_delta(state, push_delta)

        # Act
        popped, delta = manager.pop_flow(state, result=FlowContextState.COMPLETED)
        apply_delta(state, delta)

        # Assert
        assert len(state["flow_stack"]) == 0
        assert popped["flow_name"] == "flow1"
        assert popped["flow_state"] == "completed"
        assert isinstance(delta, FlowDelta)


class TestFlowManagerSlots:
    """Tests for slot management."""

    def test_set_and_get_slot(self):
        """
        GIVEN active flow
        WHEN set_slot is called
        THEN get_slot returns the value
        """
        # Arrange
        state = create_empty_dialogue_state()
        manager = FlowManager()
        _, push_delta = manager.push_flow(state, "flow1")
        apply_delta(state, push_delta)

        # Act
        delta = manager.set_slot(state, "destination", "Paris")
        apply_delta(state, delta)
        value = manager.get_slot(state, "destination")

        # Assert
        assert value == "Paris"

    def test_set_slot_returns_flow_delta(self):
        """
        GIVEN active flow
        WHEN set_slot is called
        THEN returns FlowDelta with updated flow_slots
        """
        # Arrange
        state = create_empty_dialogue_state()
        manager = FlowManager()
        flow_id, push_delta = manager.push_flow(state, "flow1")
        apply_delta(state, push_delta)

        # Act
        delta = manager.set_slot(state, "key", "value")

        # Assert
        assert isinstance(delta, FlowDelta)
        assert delta.flow_slots is not None
        assert delta.flow_slots[flow_id]["key"] == "value"

    def test_get_slot_returns_none_if_not_found(self):
        # Arrange
        state = create_empty_dialogue_state()
        manager = FlowManager()
        _, push_delta = manager.push_flow(state, "flow1")
        apply_delta(state, push_delta)

        # Act
        value = manager.get_slot(state, "non_existent")

        # Assert
        assert value is None

    def test_get_all_slots(self):
        # Arrange
        state = create_empty_dialogue_state()
        manager = FlowManager()
        _, push_delta = manager.push_flow(state, "flow1")
        apply_delta(state, push_delta)

        delta1 = manager.set_slot(state, "a", 1)
        apply_delta(state, delta1)
        delta2 = manager.set_slot(state, "b", 2)
        apply_delta(state, delta2)

        # Act
        slots = manager.get_all_slots(state)

        # Assert
        assert slots == {"a": 1, "b": 2}


class TestFlowManagerStep:
    """Tests for step advancement."""

    def test_advance_step_returns_delta(self):
        # Arrange
        state = create_empty_dialogue_state()
        manager = FlowManager()
        _, push_delta = manager.push_flow(state, "flow1")
        apply_delta(state, push_delta)

        # Act
        delta = manager.advance_step(state)
        apply_delta(state, delta)

        # Assert
        assert isinstance(delta, FlowDelta)
        assert state["flow_stack"][0]["step_index"] == 1

    def test_advance_step_returns_none_on_empty_stack(self):
        # Arrange
        state = create_empty_dialogue_state()
        manager = FlowManager()

        # Act
        delta = manager.advance_step(state)

        # Assert
        assert delta is None


class TestFlowManagerEdgeCases:
    """Tests for edge cases and optional methods."""

    def test_handle_intent_change_pushes_new_flow(self):
        # Arrange
        state = create_empty_dialogue_state()
        manager = FlowManager()

        # Act
        delta = manager.handle_intent_change(state, "new_flow")
        apply_delta(state, delta)

        # Assert
        assert len(state["flow_stack"]) == 1
        assert state["flow_stack"][0]["flow_name"] == "new_flow"

    def test_handle_intent_change_skips_push_when_same_flow_active(self):
        """
        GIVEN a flow already active on the stack
        WHEN handle_intent_change is called with the same flow name
        THEN the flow is NOT pushed again (preserves existing slots)

        This prevents slot loss after digressions when user "restarts" same flow.
        """
        # Arrange
        state = create_empty_dialogue_state()
        manager = FlowManager()
        original_flow_id, push_delta = manager.push_flow(state, "transfer_funds")
        apply_delta(state, push_delta)
        slot_delta = manager.set_slot(state, "iban", "ES123456789")
        apply_delta(state, slot_delta)

        # Act - Try to start same flow again (simulates NLU detecting StartFlow)
        delta = manager.handle_intent_change(state, "transfer_funds")

        # Assert - Should return None (no changes) and preserve slots
        assert delta is None
        assert len(state["flow_stack"]) == 1
        assert state["flow_stack"][0]["flow_id"] == original_flow_id
        assert manager.get_slot(state, "iban") == "ES123456789"

    def test_handle_intent_change_pushes_different_flow(self):
        """
        GIVEN a flow already active on the stack
        WHEN handle_intent_change is called with a DIFFERENT flow name
        THEN the new flow IS pushed (true intent switch)
        """
        # Arrange
        state = create_empty_dialogue_state()
        manager = FlowManager()
        _, push_delta = manager.push_flow(state, "transfer_funds")
        apply_delta(state, push_delta)

        # Act - Switch to different flow
        delta = manager.handle_intent_change(state, "check_balance")
        apply_delta(state, delta)

        # Assert - Should have 2 flows on stack
        assert len(state["flow_stack"]) == 2
        assert state["flow_stack"][0]["flow_name"] == "transfer_funds"
        assert state["flow_stack"][1]["flow_name"] == "check_balance"

    def test_get_active_context_returns_none_on_empty_stack(self):
        # Arrange
        state = create_empty_dialogue_state()
        manager = FlowManager()

        # Act
        context = manager.get_active_context(state)

        # Assert
        assert context is None

    def test_set_slot_returns_none_on_empty_stack(self):
        # Arrange
        state = create_empty_dialogue_state()
        manager = FlowManager()

        # Act
        delta = manager.set_slot(state, "key", "value")

        # Assert
        assert delta is None
        assert state["flow_slots"] == {}

    def test_get_all_slots_returns_empty_dict_on_empty_stack(self):
        # Arrange
        state = create_empty_dialogue_state()
        manager = FlowManager()

        # Act
        slots = manager.get_all_slots(state)

        # Assert
        assert slots == {}


class TestMergeDelta:
    """Tests for merge_delta helper function."""

    def test_merge_delta_with_none(self):
        # Arrange
        updates = {"key": "value"}

        # Act
        merge_delta(updates, None)

        # Assert
        assert updates == {"key": "value"}

    def test_merge_delta_with_flow_stack(self):
        # Arrange
        updates: dict[str, Any] = {}
        # Use cast or create full context to satisfy mypy
        dummy_context: Any = {"flow_id": "123"}
        delta = FlowDelta(flow_stack=[dummy_context], flow_slots=None)

        # Act
        merge_delta(updates, delta)

        # Assert
        assert updates["flow_stack"] == [{"flow_id": "123"}]
        assert "flow_slots" not in updates

    def test_merge_delta_with_flow_slots(self):
        # Arrange
        updates: dict[str, Any] = {}
        delta = FlowDelta(flow_stack=None, flow_slots={"id1": {"key": "val"}})

        # Act
        merge_delta(updates, delta)

        # Assert
        assert updates["flow_slots"] == {"id1": {"key": "val"}}
        assert "flow_stack" not in updates

    def test_merge_delta_with_both(self):
        # Arrange
        updates: dict[str, Any] = {"existing": True}
        dummy_context: Any = {"flow_id": "123"}
        delta = FlowDelta(flow_stack=[dummy_context], flow_slots={"id1": {"key": "val"}})

        # Act
        merge_delta(updates, delta)

        # Assert
        assert updates["existing"] is True
        assert updates["flow_stack"] == [{"flow_id": "123"}]
        assert updates["flow_slots"] == {"id1": {"key": "val"}}
