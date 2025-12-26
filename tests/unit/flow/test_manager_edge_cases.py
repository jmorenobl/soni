import pytest

from soni.core.errors import FlowStackError
from soni.core.state import create_empty_state
from soni.flow.manager import FlowManager


class TestFlowManagerEdgeCases:
    """Tests for flow manager edge cases."""

    def test_pop_from_empty_stack_fails(self):
        """Popping from an empty flow stack should raise error."""
        manager = FlowManager()
        state = create_empty_state()

        with pytest.raises(FlowStackError):
            manager.pop_flow(state)

    def test_get_active_from_empty_stack(self):
        """Getting active context from empty stack should return None."""
        manager = FlowManager()
        state = create_empty_state()

        assert manager.get_active_context(state) is None

    def test_push_multiple_flows_maintains_order(self):
        """Stack should maintain correct LIFO order."""
        manager = FlowManager()
        state = create_empty_state()

        # In FlowManager, push_flow returns (flow_id, delta)
        # We must apply the delta to see the change
        _, delta1 = manager.push_flow(state, "flow1")
        state.update(delta1.to_dict())

        _, delta2 = manager.push_flow(state, "flow2")
        state.update(delta2.to_dict())

        active = manager.get_active_context(state)
        assert active["flow_name"] == "flow2"
        assert len(state["flow_stack"]) == 2

    def test_handle_intent_change_duplicate(self):
        """Should return None if intent change is to already active flow."""
        manager = FlowManager()
        state = create_empty_state()

        _, delta = manager.push_flow(state, "test_flow")
        state.update(delta.to_dict())

        # Change to same flow
        delta2 = manager.handle_intent_change(state, "test_flow")
        assert delta2 is None

    def test_handle_intent_change_new(self):
        """Should return delta if intent change is to different flow."""
        manager = FlowManager()
        state = create_empty_state()

        # Change from empty
        delta = manager.handle_intent_change(state, "flow1")
        assert delta is not None
        assert delta.flow_stack[-1]["flow_name"] == "flow1"

    def test_slot_access_without_context(self):
        """Slots should be None/empty without active context."""
        manager = FlowManager()
        state = create_empty_state()

        assert manager.get_slot(state, "any") is None
        assert manager.get_all_slots(state) == {}
        assert manager.set_slot(state, "s", "v") is None

    def test_advance_step_without_context(self):
        """Advancing step should return None without active context."""
        manager = FlowManager()
        state = create_empty_state()
        assert manager.advance_step(state) is None

    def test_get_active_flow_id(self):
        """Should return active flow ID or None."""
        manager = FlowManager()
        state = create_empty_state()
        assert manager.get_active_flow_id(state) is None

        _, delta = manager.push_flow(state, "test")
        state.update(delta.to_dict())
        assert manager.get_active_flow_id(state) is not None

    def test_get_slot_none_slots(self):
        """Should handle state['flow_slots'] being None."""
        manager = FlowManager()
        state = create_empty_state()
        _, delta = manager.push_flow(state, "test")
        state.update(delta.to_dict())
        state["flow_slots"] = None
        assert manager.get_slot(state, "any") is None
        assert manager.get_all_slots(state) == {}

    def test_apply_delta_none(self):
        """apply_delta_to_dict should do nothing if delta is None."""
        from soni.flow.manager import apply_delta_to_dict

        state = {}
        apply_delta_to_dict(state, None)
        assert state == {}

    def test_pop_flow_success(self):
        """Should pop flow and return its context."""
        manager = FlowManager()
        state = create_empty_state()
        _, delta = manager.push_flow(state, "test")
        state.update(delta.to_dict())

        popped, delta2 = manager.pop_flow(state)
        assert popped["flow_name"] == "test"
        assert len(delta2.flow_stack) == 0

    def test_slot_access_success(self):
        """Should get and set slots correctly with active context."""
        manager = FlowManager()
        state = create_empty_state()
        _, delta = manager.push_flow(state, "test")
        state.update(delta.to_dict())

        # Set slot
        delta2 = manager.set_slot(state, "amount", 100)
        state.update(delta2.to_dict())

        assert manager.get_slot(state, "amount") == 100
        assert manager.get_all_slots(state) == {"amount": 100}

    def test_advance_step_success(self):
        """Should increment step index in active context."""
        manager = FlowManager()
        state = create_empty_state()
        _, delta = manager.push_flow(state, "test")
        state.update(delta.to_dict())

        assert state["flow_stack"][-1]["step_index"] == 0
        delta2 = manager.advance_step(state)
        state.update(delta2.to_dict())
        assert state["flow_stack"][-1]["step_index"] == 1
