"""Tests for state access helper functions."""

import pytest

from soni.core.state import (
    get_action_result,
    get_conversation_state,
    get_current_flow_context,
    get_flow_stack,
    get_last_response,
    get_metadata,
    get_nlu_result,
    get_user_message,
)


class TestGetNLUResult:
    """Tests for get_nlu_result helper."""

    def test_returns_nlu_result_when_present(self):
        """Test returns NLU result when present in state."""
        state = {"nlu_result": {"intent": "book_flight"}}
        result = get_nlu_result(state)
        assert result == {"intent": "book_flight"}

    def test_returns_empty_dict_when_none(self):
        """Test returns empty dict when nlu_result is None."""
        state = {"nlu_result": None}
        result = get_nlu_result(state)
        assert result == {}

    def test_returns_empty_dict_when_missing(self):
        """Test returns empty dict when nlu_result not in state."""
        state = {}
        result = get_nlu_result(state)
        assert result == {}


class TestGetMetadata:
    """Tests for get_metadata helper."""

    def test_returns_metadata_when_present(self):
        """Test returns metadata when present."""
        state = {"metadata": {"key": "value"}}
        result = get_metadata(state)
        assert result == {"key": "value"}

    def test_returns_empty_dict_when_missing(self):
        """Test returns empty dict when metadata not in state."""
        state = {}
        result = get_metadata(state)
        assert result == {}


class TestGetConversationState:
    """Tests for get_conversation_state helper."""

    def test_returns_state_when_present(self):
        """Test returns conversation state when present."""
        state = {"conversation_state": "understanding"}
        result = get_conversation_state(state)
        assert result == "understanding"

    def test_returns_default_when_missing(self):
        """Test returns 'idle' default when missing."""
        state = {}
        result = get_conversation_state(state)
        assert result == "idle"

    def test_returns_custom_default(self):
        """Test returns custom default when specified."""
        state = {}
        result = get_conversation_state(state, default="custom")
        assert result == "custom"


class TestGetFlowStack:
    """Tests for get_flow_stack helper."""

    def test_returns_flow_stack_when_present(self):
        """Test returns flow stack when present."""
        stack = [{"flow_id": "flow1"}]
        state = {"flow_stack": stack}
        result = get_flow_stack(state)
        assert result == stack

    def test_returns_empty_list_when_missing(self):
        """Test returns empty list when missing."""
        state = {}
        result = get_flow_stack(state)
        assert result == []


class TestGetCurrentFlowContext:
    """Tests for get_current_flow_context helper."""

    def test_returns_top_flow_when_stack_not_empty(self):
        """Test returns top flow from stack."""
        state = {
            "flow_stack": [
                {"flow_id": "flow1"},
                {"flow_id": "flow2"},  # This should be returned
            ]
        }
        result = get_current_flow_context(state)
        assert result == {"flow_id": "flow2"}

    def test_returns_none_when_stack_empty(self):
        """Test returns None when flow stack is empty."""
        state = {"flow_stack": []}
        result = get_current_flow_context(state)
        assert result is None

    def test_returns_none_when_stack_missing(self):
        """Test returns None when flow_stack not in state."""
        state = {}
        result = get_current_flow_context(state)
        assert result is None


class TestOtherHelpers:
    """Tests for other state helpers."""

    def test_get_user_message(self):
        """Test get_user_message helper."""
        state = {"user_message": "hello"}
        assert get_user_message(state) == "hello"
        assert get_user_message({}) == ""

    def test_get_last_response(self):
        """Test get_last_response helper."""
        state = {"last_response": "How can I help?"}
        assert get_last_response(state) == "How can I help?"
        assert get_last_response({}) == ""

    def test_get_action_result(self):
        """Test get_action_result helper."""
        state = {"action_result": {"status": "success"}}
        assert get_action_result(state) == {"status": "success"}
        assert get_action_result({}) is None
