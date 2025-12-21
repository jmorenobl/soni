"""Edge case tests for FlowManager operations.

Tests complex flow stack scenarios and edge cases.
"""

import pytest

from soni.core.errors import FlowStackError
from soni.core.state import create_empty_dialogue_state
from soni.flow.manager import FlowDelta, FlowManager, merge_delta


class TestFlowStackEdgeCases:
    """Edge case tests for flow stack operations."""

    @pytest.fixture
    def flow_manager(self):
        return FlowManager()

    @pytest.fixture
    def empty_state(self):
        return create_empty_dialogue_state()

    def test_pop_empty_stack_raises_error(self, flow_manager, empty_state):
        """Test that popping empty stack raises FlowStackError."""
        with pytest.raises(FlowStackError) as exc_info:
            flow_manager.pop_flow(empty_state)

        assert "empty" in str(exc_info.value).lower()

    def test_multiple_flows_stacked(self, flow_manager, empty_state):
        """Test pushing multiple flows creates proper stack."""
        # Push three flows
        flow_id1, delta1 = flow_manager.push_flow(empty_state, "flow1")
        state1 = {
            **empty_state,
            "flow_stack": delta1.flow_stack,
            "flow_slots": delta1.flow_slots,
        }

        flow_id2, delta2 = flow_manager.push_flow(state1, "flow2")
        state2 = {
            **state1,
            "flow_stack": delta2.flow_stack,
            "flow_slots": delta2.flow_slots,
        }

        flow_id3, delta3 = flow_manager.push_flow(state2, "flow3")
        final_state = {
            **state2,
            "flow_stack": delta3.flow_stack,
            "flow_slots": delta3.flow_slots,
        }

        assert len(final_state["flow_stack"]) == 3
        assert final_state["flow_stack"][-1]["flow_name"] == "flow3"
        assert final_state["flow_stack"][0]["flow_name"] == "flow1"
        # Verify flow IDs are unique
        flow_ids = [ctx["flow_id"] for ctx in final_state["flow_stack"]]
        assert len(set(flow_ids)) == 3

    def test_pop_preserves_underlying_flows(self, flow_manager, empty_state):
        """Test that popping top flow preserves flows underneath."""
        # Push two flows
        flow_id1, delta1 = flow_manager.push_flow(empty_state, "flow1")
        state1 = {
            **empty_state,
            "flow_stack": delta1.flow_stack,
            "flow_slots": delta1.flow_slots,
        }

        flow_id2, delta2 = flow_manager.push_flow(state1, "flow2")
        state2 = {
            **state1,
            "flow_stack": delta2.flow_stack,
            "flow_slots": delta2.flow_slots,
        }

        # Pop top flow
        popped, delta3 = flow_manager.pop_flow(state2)

        assert popped["flow_name"] == "flow2"
        assert len(delta3.flow_stack) == 1
        assert delta3.flow_stack[0]["flow_name"] == "flow1"

    def test_intent_change_to_same_flow_returns_none(self, flow_manager, empty_state):
        """Test that intent change to same active flow is no-op."""
        # Start flow
        _, delta1 = flow_manager.push_flow(empty_state, "greeting")
        state1 = {
            **empty_state,
            "flow_stack": delta1.flow_stack,
            "flow_slots": delta1.flow_slots,
        }

        # Intent change to same flow
        delta2 = flow_manager.handle_intent_change(state1, "greeting")

        assert delta2 is None  # No change

    def test_intent_change_during_active_flow(self, flow_manager, empty_state):
        """Test that intent change during flow pushes new flow on stack."""
        # Start first flow
        _, delta1 = flow_manager.push_flow(empty_state, "booking")
        state1 = {
            **empty_state,
            "flow_stack": delta1.flow_stack,
            "flow_slots": delta1.flow_slots,
        }

        # Intent change to different flow
        delta2 = flow_manager.handle_intent_change(state1, "help")

        assert delta2 is not None
        assert len(delta2.flow_stack) == 2
        assert delta2.flow_stack[-1]["flow_name"] == "help"

    def test_set_slot_without_active_flow_returns_none(self, flow_manager, empty_state):
        """Test that setting slot without active flow is no-op."""
        delta = flow_manager.set_slot(empty_state, "some_slot", "value")

        assert delta is None

    def test_get_slot_without_active_flow_returns_none(self, flow_manager, empty_state):
        """Test that getting slot without active flow returns None."""
        result = flow_manager.get_slot(empty_state, "some_slot")

        assert result is None

    def test_slots_isolated_between_flow_instances(self, flow_manager, empty_state):
        """Test that slots are isolated between different flow instances."""
        # Push flow1 and set slot
        flow_id1, delta1 = flow_manager.push_flow(empty_state, "booking")
        state1 = {
            **empty_state,
            "flow_stack": delta1.flow_stack,
            "flow_slots": delta1.flow_slots,
        }

        delta_slot1 = flow_manager.set_slot(state1, "amount", 100)
        state1 = {**state1, "flow_slots": delta_slot1.flow_slots}

        # Push same flow again (new instance)
        flow_id2, delta2 = flow_manager.push_flow(state1, "booking")
        state2 = {
            **state1,
            "flow_stack": delta2.flow_stack,
            "flow_slots": delta2.flow_slots,
        }

        # Verify different flow_ids
        assert flow_id1 != flow_id2

        # Verify slots are separate
        assert state2["flow_slots"][flow_id1]["amount"] == 100
        assert flow_id2 not in state2["flow_slots"] or "amount" not in state2["flow_slots"].get(
            flow_id2, {}
        )


class TestFlowDeltaMerging:
    """Tests for FlowDelta merge operations."""

    def test_merge_delta_with_none(self):
        """Test that merging None delta does nothing."""
        updates: dict[str, str] = {"existing": "value"}
        merge_delta(updates, None)

        assert updates == {"existing": "value"}

    def test_merge_delta_with_only_stack(self):
        """Test merging delta with only flow_stack."""
        updates: dict = {}
        delta = FlowDelta(flow_stack=[{"flow_id": "test"}])

        merge_delta(updates, delta)

        assert "flow_stack" in updates
        assert "flow_slots" not in updates

    def test_merge_delta_with_only_slots(self):
        """Test merging delta with only flow_slots."""
        updates: dict = {}
        delta = FlowDelta(flow_slots={"test": {"slot": "value"}})

        merge_delta(updates, delta)

        assert "flow_slots" in updates
        assert "flow_stack" not in updates

    def test_merge_delta_preserves_existing_updates(self):
        """Test that merge preserves non-flow updates."""
        updates: dict = {"response": "hello", "turn_count": 5}
        delta = FlowDelta(flow_stack=[])

        merge_delta(updates, delta)

        assert updates["response"] == "hello"
        assert updates["turn_count"] == 5
        assert updates["flow_stack"] == []

    def test_multiple_deltas_in_sequence(self):
        """Test applying multiple deltas in sequence."""
        updates: dict = {}

        delta1 = FlowDelta(flow_stack=[{"flow_id": "f1"}])
        delta2 = FlowDelta(flow_slots={"f1": {"slot1": "v1"}})
        delta3 = FlowDelta(
            flow_stack=[{"flow_id": "f1"}, {"flow_id": "f2"}],
            flow_slots={"f1": {"slot1": "v1"}, "f2": {}},
        )

        merge_delta(updates, delta1)
        merge_delta(updates, delta2)
        merge_delta(updates, delta3)

        # Last delta should win for overlapping keys
        assert len(updates["flow_stack"]) == 2
        assert "f2" in updates["flow_slots"]
