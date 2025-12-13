"""Test constants module (DM-002: Eliminate Magic Strings).

TDD Red Phase: These tests should FAIL until constants.py is implemented.
"""

import pytest


class TestConversationState:
    """Test ConversationState enum."""

    def test_can_import(self):
        """ConversationState should be importable from core.constants."""
        from soni.core.constants import ConversationState

        assert ConversationState is not None

    def test_all_states_are_strings(self):
        """Verify all states can be used as strings (StrEnum)."""
        from soni.core.constants import ConversationState

        for state in ConversationState:
            assert isinstance(state.value, str)
            # StrEnum allows direct string comparison
            assert state == state.value

    def test_confirming_value(self):
        """Test specific state value matches expected string."""
        from soni.core.constants import ConversationState

        assert ConversationState.CONFIRMING == "confirming"
        assert ConversationState.WAITING_FOR_SLOT == "waiting_for_slot"
        assert ConversationState.READY_FOR_ACTION == "ready_for_action"

    def test_invalid_state_not_in_enum(self):
        """Test that typo strings don't match any state."""
        from soni.core.constants import ConversationState

        invalid_typos = ["confirmng", "waitng_for_slot", "redyforaction"]
        valid_values = {s.value for s in ConversationState}

        for typo in invalid_typos:
            assert typo not in valid_values

    def test_required_states_exist(self):
        """Verify all required states from routing.py exist."""
        from soni.core.constants import ConversationState

        required_states = {
            "idle",
            "understanding",
            "waiting_for_slot",
            "ready_for_confirmation",
            "confirming",
            "ready_for_action",
            "generating_response",
            "completed",
            "error",
        }
        actual_values = {s.value for s in ConversationState}
        assert required_states <= actual_values


class TestNodeName:
    """Test NodeName enum."""

    def test_can_import(self):
        """NodeName should be importable from core.constants."""
        from soni.core.constants import NodeName

        assert NodeName is not None

    def test_all_nodes_are_strings(self):
        """Verify all node names can be used as strings."""
        from soni.core.constants import NodeName

        for node in NodeName:
            assert isinstance(node.value, str)
            assert node == node.value

    def test_specific_node_values(self):
        """Test specific node values match expected strings."""
        from soni.core.constants import NodeName

        assert NodeName.EXECUTE_ACTION == "execute_action"
        assert NodeName.GENERATE_RESPONSE == "generate_response"
        assert NodeName.HANDLE_CONFIRMATION == "handle_confirmation"

    def test_routing_targets_exist(self):
        """Verify all routing targets from routing.py exist as node names."""
        from soni.core.constants import NodeName

        # These are all the return values from routing functions
        required_nodes = {
            "understand",
            "validate_slot",
            "collect_next_slot",
            "confirm_action",
            "execute_action",
            "generate_response",
            "handle_digression",
            "handle_correction",
            "handle_modification",
            "handle_confirmation",
            "handle_intent_change",
            "handle_clarification",
            "handle_cancellation",
        }
        actual_values = {n.value for n in NodeName}
        assert required_nodes <= actual_values


class TestMessageTypeReexport:
    """Test that MessageType is re-exported from constants."""

    def test_can_import_message_type(self):
        """MessageType should be importable from core.constants."""
        from soni.core.constants import MessageType

        assert MessageType is not None

    def test_message_type_values(self):
        """Verify MessageType has expected values."""
        from soni.core.constants import MessageType

        assert MessageType.SLOT_VALUE == "slot_value"
        assert MessageType.CORRECTION == "correction"
        assert MessageType.CONFIRMATION == "confirmation"

    def test_same_as_du_models(self):
        """Verify it's the same enum as du.models.MessageType."""
        from soni.core.constants import MessageType as ConstantsMessageType
        from soni.du.models import MessageType as DUMessageType

        assert ConstantsMessageType is DUMessageType
