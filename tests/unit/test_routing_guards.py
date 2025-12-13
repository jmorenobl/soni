"""Test confirming state guard (DM-003).

Tests for _redirect_if_confirming guard function.
"""

import pytest

from soni.core.constants import ConversationState, NodeName


class TestRedirectIfConfirming:
    """Test _redirect_if_confirming guard function."""

    def test_guard_exists_and_importable(self):
        """Guard should be importable from routing module."""
        from soni.dm.routing import _redirect_if_confirming

        assert callable(_redirect_if_confirming)

    def test_confirming_state_returns_handle_confirmation(self):
        """When in CONFIRMING state, should return HANDLE_CONFIRMATION."""
        from soni.dm.routing import _redirect_if_confirming

        state = {"conversation_state": ConversationState.CONFIRMING}

        result = _redirect_if_confirming(state, "slot_value")
        assert result == NodeName.HANDLE_CONFIRMATION

    def test_non_confirming_state_returns_none(self):
        """When NOT in confirming state, should return None."""
        from soni.dm.routing import _redirect_if_confirming

        state = {"conversation_state": ConversationState.WAITING_FOR_SLOT}

        result = _redirect_if_confirming(state, "slot_value")
        assert result is None

    def test_none_state_returns_none(self):
        """When state is None, should return None."""
        from soni.dm.routing import _redirect_if_confirming

        state = {"conversation_state": None}

        result = _redirect_if_confirming(state, "slot_value")
        assert result is None


class TestGuardIntegration:
    """Test that handlers use the guard function."""

    def test_slot_value_uses_guard(self):
        """_route_slot_value should use _redirect_if_confirming."""
        import inspect

        from soni.dm.routing import _route_slot_value

        source = inspect.getsource(_route_slot_value)
        assert "_redirect_if_confirming" in source

    def test_correction_uses_guard(self):
        """_route_correction should use _redirect_if_confirming."""
        import inspect

        from soni.dm.routing import _route_correction

        source = inspect.getsource(_route_correction)
        assert "_redirect_if_confirming" in source

    def test_modification_uses_guard(self):
        """_route_modification should use _redirect_if_confirming."""
        import inspect

        from soni.dm.routing import _route_modification

        source = inspect.getsource(_route_modification)
        assert "_redirect_if_confirming" in source
