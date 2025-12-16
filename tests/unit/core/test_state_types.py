"""Unit tests for core types."""
import pytest

from soni.core.state import create_empty_dialogue_state
from soni.core.types import DialogueState


class TestDialogueState:
    """Tests for DialogueState TypedDict."""

    def test_create_empty_dialogue_state_returns_valid_structure(self):
        """
        GIVEN nothing
        WHEN create_empty_dialogue_state is called
        THEN returns a valid DialogueState with all required keys
        """
        # Act
        state = create_empty_dialogue_state()

        # Assert
        assert state["flow_stack"] == []
        assert state["flow_slots"] == {}
        assert state["turn_count"] == 0
        assert state["messages"] == []
        assert state["user_message"] is None
        assert state["last_response"] == ""
        assert state["action_result"] is None

    def test_dialogue_state_is_json_serializable(self):
        """
        GIVEN a DialogueState
        WHEN serialized to JSON
        THEN no errors occur and can be deserialized
        """
        import json

        # Arrange
        state = create_empty_dialogue_state()
        # Add some dummy data
        state["user_message"] = "Hello"
        state["flow_stack"].append({
            "flow_id": "test-123",
            "flow_name": "test",
            "flow_state": "active",
            "current_step": "start",
            "step_index": 0,
            "outputs": {},
            "started_at": 100.0,
        })

        # Act
        json_str = json.dumps(state)
        restored = json.loads(json_str)

        # Assert
        assert restored["user_message"] == "Hello"
        assert restored["flow_stack"][0]["flow_id"] == "test-123"

    def test_dialogue_state_isolation(self):
        """
        GIVEN two dialogue states
        WHEN one is modified
        THEN the other remains unchanged
        """
        # Arrange
        state1 = create_empty_dialogue_state()
        state2 = create_empty_dialogue_state()

        # Act
        state1["flow_stack"].append({"id": 1})

        # Assert
        assert len(state1["flow_stack"]) == 1
        assert len(state2["flow_stack"]) == 0
