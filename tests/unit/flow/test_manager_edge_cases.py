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
