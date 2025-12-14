"""Unit tests for conversation state semantics and validation."""

import pytest

from soni.core.constants import ConversationState
from soni.core.state_semantics import STATE_SEMANTICS, validate_conversation_state


class TestStateSemantics:
    """Test suite for state semantics table and validation."""

    def test_state_semantics_completeness(self):
        """Verify that all conversation states have a semantic definition."""
        for state in ConversationState:
            assert state in STATE_SEMANTICS
            assert isinstance(STATE_SEMANTICS[state], str)
            assert len(STATE_SEMANTICS[state]) > 0

    def test_semantics_keys_match_enum(self):
        """Verify that STATE_SEMANTICS keys match ConversationState enum."""
        assert set(STATE_SEMANTICS.keys()) == set(ConversationState)

    def test_validate_valid_states(self):
        """Verify validation of valid state strings."""
        for state in ConversationState:
            result = validate_conversation_state(state.value)
            assert result == state

    def test_validate_none_state(self):
        """Verify validation of None state defaults to IDLE."""
        result = validate_conversation_state(None)
        assert result == ConversationState.IDLE

    def test_validate_invalid_state(self):
        """Verify validation of invalid state string returns FALLBACK."""
        result = validate_conversation_state("invalid_state_123")
        assert result == ConversationState.FALLBACK

    def test_validate_empty_string(self):
        """Verify validation of empty string returns FALLBACK (or error if not allowed)."""
        # Empty string is not a valid state in StrEnum
        result = validate_conversation_state("")
        assert result == ConversationState.FALLBACK
