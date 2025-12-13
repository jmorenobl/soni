"""Test individual route handlers for route_after_understand (DM-001).

TDD Red Phase: Tests for the dispatch pattern refactoring.
"""

import pytest

from soni.core.constants import ConversationState, MessageType, NodeName


class TestRouteHandlersExist:
    """Test that all route handlers are exported and callable."""

    def test_route_handlers_dict_exists(self):
        """ROUTE_HANDLERS dictionary should be importable."""
        from soni.dm.routing import ROUTE_HANDLERS

        assert isinstance(ROUTE_HANDLERS, dict)

    def test_route_handlers_has_all_message_types(self):
        """ROUTE_HANDLERS should cover all expected message types."""
        from soni.dm.routing import ROUTE_HANDLERS

        expected_types = {
            "slot_value",
            "correction",
            "modification",
            "interruption",
            "intent_change",
            "clarification",
            "digression",
            "question",
            "cancellation",
            "confirmation",
            "continuation",
        }
        assert expected_types <= set(ROUTE_HANDLERS.keys())

    def test_all_handlers_are_callable(self):
        """All handlers in ROUTE_HANDLERS should be callable."""
        from soni.dm.routing import ROUTE_HANDLERS

        for msg_type, handler in ROUTE_HANDLERS.items():
            assert callable(handler), f"Handler for {msg_type} is not callable"


class TestNormalizeMessageType:
    """Test message type normalization helper."""

    def test_normalize_string(self):
        """String message type should be normalized to lowercase."""
        from soni.dm.routing import _normalize_message_type

        assert _normalize_message_type("SLOT_VALUE") == "slot_value"
        assert _normalize_message_type("Correction") == "correction"

    def test_normalize_enum(self):
        """Enum message type should be normalized to its string value."""
        from soni.dm.routing import _normalize_message_type

        assert _normalize_message_type(MessageType.SLOT_VALUE) == "slot_value"
        assert _normalize_message_type(MessageType.CONFIRMATION) == "confirmation"

    def test_normalize_none_returns_none(self):
        """None should return None."""
        from soni.dm.routing import _normalize_message_type

        assert _normalize_message_type(None) is None


class TestRouteSlotValue:
    """Test _route_slot_value handler."""

    def test_confirming_state_redirects_to_confirmation(self):
        """In confirming state, slot_value should redirect to handle_confirmation."""
        from soni.dm.routing import _route_slot_value

        state = {"conversation_state": ConversationState.CONFIRMING}
        nlu_result = {"message_type": "slot_value", "slots": []}

        result = _route_slot_value(state, nlu_result)
        assert result == NodeName.HANDLE_CONFIRMATION

    def test_no_active_flow_with_command_starts_flow(self):
        """No active flow but has command should start flow first."""
        from soni.dm.routing import _route_slot_value

        state = {"conversation_state": "idle", "flow_stack": []}
        nlu_result = {"message_type": "slot_value", "slots": [], "command": "book_flight"}

        result = _route_slot_value(state, nlu_result)
        assert result == NodeName.HANDLE_INTENT_CHANGE

    def test_active_flow_goes_to_validate(self):
        """With active flow, should go to validate_slot."""
        from soni.dm.routing import _route_slot_value

        state = {
            "conversation_state": "waiting_for_slot",
            "flow_stack": [{"flow_name": "book_flight"}],
        }
        nlu_result = {"message_type": "slot_value", "slots": []}

        result = _route_slot_value(state, nlu_result)
        assert result == NodeName.VALIDATE_SLOT


class TestRouteCorrection:
    """Test _route_correction handler."""

    def test_confirming_state_redirects_to_confirmation(self):
        """In confirming state, correction should redirect to handle_confirmation."""
        from soni.dm.routing import _route_correction

        state = {"conversation_state": ConversationState.CONFIRMING}
        nlu_result = {"message_type": "correction", "slots": []}

        result = _route_correction(state, nlu_result)
        assert result == NodeName.HANDLE_CONFIRMATION

    def test_normal_state_goes_to_correction_handler(self):
        """In normal state, should go to handle_correction."""
        from soni.dm.routing import _route_correction

        state = {
            "conversation_state": "waiting_for_slot",
            "flow_stack": [{"flow_name": "test"}],
        }
        nlu_result = {"message_type": "correction", "slots": []}

        result = _route_correction(state, nlu_result)
        assert result == NodeName.HANDLE_CORRECTION


class TestRouteModification:
    """Test _route_modification handler."""

    def test_confirming_state_redirects_to_confirmation(self):
        """In confirming state, modification should redirect to handle_confirmation."""
        from soni.dm.routing import _route_modification

        state = {"conversation_state": ConversationState.CONFIRMING}
        nlu_result = {"message_type": "modification", "slots": []}

        result = _route_modification(state, nlu_result)
        assert result == NodeName.HANDLE_CONFIRMATION

    def test_normal_state_goes_to_modification_handler(self):
        """In normal state, should go to handle_modification."""
        from soni.dm.routing import _route_modification

        state = {
            "conversation_state": "waiting_for_slot",
            "flow_stack": [{"flow_name": "test"}],
        }
        nlu_result = {"message_type": "modification", "slots": []}

        result = _route_modification(state, nlu_result)
        assert result == NodeName.HANDLE_MODIFICATION


class TestRouteConfirmation:
    """Test _route_confirmation handler."""

    def test_confirming_state_goes_to_handle_confirmation(self):
        """In confirming state, should go to handle_confirmation."""
        from soni.dm.routing import _route_confirmation

        state = {"conversation_state": ConversationState.CONFIRMING}
        nlu_result = {"message_type": "confirmation"}

        result = _route_confirmation(state, nlu_result)
        assert result == NodeName.HANDLE_CONFIRMATION

    def test_ready_for_confirmation_goes_to_handle_confirmation(self):
        """In ready_for_confirmation state, should go to handle_confirmation."""
        from soni.dm.routing import _route_confirmation

        state = {"conversation_state": ConversationState.READY_FOR_CONFIRMATION}
        nlu_result = {"message_type": "confirmation"}

        result = _route_confirmation(state, nlu_result)
        assert result == NodeName.HANDLE_CONFIRMATION

    def test_other_state_with_active_flow_collects_slot(self):
        """In other state with active flow, should collect_next_slot."""
        from soni.dm.routing import _route_confirmation

        state = {
            "conversation_state": "waiting_for_slot",
            "flow_stack": [{"flow_name": "test"}],
        }
        nlu_result = {"message_type": "confirmation"}

        result = _route_confirmation(state, nlu_result)
        assert result == NodeName.COLLECT_NEXT_SLOT


class TestRouteContinuation:
    """Test _route_continuation handler."""

    def test_active_flow_collects_next_slot(self):
        """With active flow, should collect next slot."""
        from soni.dm.routing import _route_continuation

        state = {
            "conversation_state": "waiting_for_slot",
            "flow_stack": [{"flow_name": "test"}],
        }
        nlu_result = {"message_type": "continuation"}

        result = _route_continuation(state, nlu_result)
        assert result == NodeName.COLLECT_NEXT_SLOT

    def test_no_flow_with_command_starts_flow(self):
        """No active flow but has command should start flow."""
        from soni.dm.routing import _route_continuation

        state = {"conversation_state": "idle", "flow_stack": []}
        nlu_result = {"message_type": "continuation", "command": "book_flight"}

        result = _route_continuation(state, nlu_result)
        assert result == NodeName.HANDLE_INTENT_CHANGE

    def test_no_flow_no_command_generates_response(self):
        """No active flow, no command should generate response."""
        from soni.dm.routing import _route_continuation

        state = {"conversation_state": "idle", "flow_stack": []}
        nlu_result = {"message_type": "continuation"}

        result = _route_continuation(state, nlu_result)
        assert result == NodeName.GENERATE_RESPONSE


class TestSimpleRouteHandlers:
    """Test simple route handlers that don't have complex logic."""

    def test_route_intent_change(self):
        """Intent change should route to handle_intent_change."""
        from soni.dm.routing import _route_intent_change

        state = {}
        nlu_result = {"message_type": "intent_change"}

        result = _route_intent_change(state, nlu_result)
        assert result == NodeName.HANDLE_INTENT_CHANGE

    def test_route_clarification(self):
        """Clarification should route to handle_clarification."""
        from soni.dm.routing import _route_clarification

        state = {}
        nlu_result = {"message_type": "clarification"}

        result = _route_clarification(state, nlu_result)
        assert result == NodeName.HANDLE_CLARIFICATION

    def test_route_digression(self):
        """Digression should route to handle_digression."""
        from soni.dm.routing import _route_digression

        state = {}
        nlu_result = {"message_type": "digression"}

        result = _route_digression(state, nlu_result)
        assert result == NodeName.HANDLE_DIGRESSION

    def test_route_cancellation(self):
        """Cancellation should route to handle_cancellation."""
        from soni.dm.routing import _route_cancellation

        state = {}
        nlu_result = {"message_type": "cancellation"}

        result = _route_cancellation(state, nlu_result)
        assert result == NodeName.HANDLE_CANCELLATION

    def test_route_fallback(self):
        """Unknown types should route to generate_response."""
        from soni.dm.routing import _route_fallback

        state = {}
        nlu_result = {"message_type": "unknown_type"}

        result = _route_fallback(state, nlu_result)
        assert result == NodeName.GENERATE_RESPONSE


class TestRouteAfterUnderstandRefactored:
    """Test that route_after_understand uses dispatch pattern."""

    def test_function_is_short(self):
        """route_after_understand should be less than 30 lines."""
        import inspect

        from soni.dm.routing import route_after_understand

        source = inspect.getsource(route_after_understand)
        lines = [line for line in source.split("\n") if line.strip()]
        # Allow some margin for docstring
        assert len(lines) < 40, f"Function has {len(lines)} lines, should be < 40"

    def test_uses_dispatch_pattern(self):
        """route_after_understand should use ROUTE_HANDLERS for routing."""
        import inspect

        from soni.dm.routing import route_after_understand

        source = inspect.getsource(route_after_understand)
        assert "ROUTE_HANDLERS" in source, "Function should use ROUTE_HANDLERS dispatch"
        assert "match message_type:" not in source, "Function should not use match statement"
