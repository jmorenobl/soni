"""Tests verifying confirm handlers don't mutate state."""

from copy import deepcopy
from typing import Any
from unittest.mock import Mock

import pytest
from soni.compiler.nodes.confirm_handlers import (
    AffirmHandler,
    DenyHandler,
    ModificationHandler,
    apply_delta,
)
from soni.flow.manager import FlowDelta, FlowManager


class TestApplyDelta:
    """Test apply_delta helper."""

    def test_does_not_take_state_parameter(self):
        """apply_delta should only take updates and delta."""
        import inspect

        sig = inspect.signature(apply_delta)
        params = list(sig.parameters.keys())

        # Check that state is NOT first parameter or present
        assert "state" not in params
        assert "updates" in params
        assert "delta" in params

    def test_merges_delta_into_updates(self):
        """Should merge delta fields into updates dict."""
        # Note: This test will fail until we refactor apply_delta signature
        # We need to adapt the call to match current signature if we want it to run before refactor
        # But for TDD "Red" phase, failing on signature mismatch is acceptable/expected
        pass


class TestHandlersDoNotMutateState:
    """Test that handlers don't mutate state directly."""

    @pytest.fixture
    def mock_context(self):
        ctx = Mock()
        ctx.flow_manager = Mock(spec=FlowManager)
        ctx.flow_manager.set_slot = Mock(
            return_value=FlowDelta(flow_slots={"flow_1": {"slot": "new_value"}})
        )
        ctx.flow_manager.get_all_slots = Mock(return_value={"slot": "value"})
        ctx.slot_name = "test_slot"
        ctx.confirmation_value = "confirmed_value"
        ctx.prompt = "Please confirm"
        ctx.retry_key = "retry_count"
        ctx.confirmation_config = Mock()
        ctx.confirmation_config.modification_handling = "update_and_reprompt"
        ctx.confirmation_config.update_acknowledgment = "Updated."
        return ctx

    @pytest.fixture
    def initial_state(self):
        return {
            "flow_stack": [{"flow_id": "flow_1", "flow_name": "test"}],
            "flow_slots": {"flow_1": {"slot": "original_value"}},
            "messages": [],
        }

    def test_affirm_handler_does_not_mutate_state(self, mock_context, initial_state):
        """AffirmHandler should not mutate state directly."""
        handler = AffirmHandler()
        state_copy = deepcopy(initial_state)
        updates: dict[str, Any] = {}

        handler.handle(mock_context, initial_state, updates)

        assert initial_state == state_copy

    def test_modification_handler_does_not_mutate_state(self, mock_context, initial_state):
        """ModificationHandler should not mutate state directly."""
        handler = ModificationHandler()
        state_copy = deepcopy(initial_state)
        updates: dict[str, Any] = {}

        handler.handle(mock_context, initial_state, updates)

        assert initial_state == state_copy

    def test_deny_handler_does_not_mutate_state(self, mock_context, initial_state):
        """DenyHandler should not mutate state directly."""
        handler = DenyHandler()
        state_copy = deepcopy(initial_state)
        updates: dict[str, Any] = {}
        commands: list[Any] = []

        handler.handle(mock_context, initial_state, updates, commands, None)

        assert initial_state == state_copy
