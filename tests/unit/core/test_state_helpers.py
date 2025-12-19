import pytest

from soni.core.constants import FlowContextState, FlowState
from soni.core.state import create_empty_dialogue_state, get_current_flow_id


class TestStateHelpers:
    """Tests for state helper functions."""

    def test_get_current_flow_id_returns_id(self):
        """Test get_current_flow_id returns ID of top flow."""
        state = create_empty_dialogue_state()
        state["flow_stack"] = [
            {
                "flow_id": "flow_1",
                "flow_name": "test",
                "flow_state": FlowContextState.ACTIVE,
                "current_step": None,
                "step_index": 0,
                "outputs": {},
                "started_at": 0.0,
            },
            {
                "flow_id": "flow_2",
                "flow_name": "test2",
                "flow_state": FlowContextState.ACTIVE,
                "current_step": None,
                "step_index": 0,
                "outputs": {},
                "started_at": 0.0,
            },
        ]
        assert get_current_flow_id(state) == "flow_2"

    def test_get_current_flow_id_returns_none_if_empty(self):
        """Test get_current_flow_id returns None if stack empty."""
        state = create_empty_dialogue_state()
        assert get_current_flow_id(state) is None
