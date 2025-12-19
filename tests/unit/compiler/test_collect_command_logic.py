"""Unit tests for command-based collect node logic.

Tests the command checking logic WITHOUT calling interrupt().
Integration tests will verify the full interrupt() flow.
"""

from unittest.mock import MagicMock

import pytest

from soni.core.commands import SetSlot


class TestCollectNodeCommandLogic:
    """Unit tests for command-based collection logic."""

    async def test_collect_node_skips_when_slot_filled(self):
        """Test that collect node returns empty dict when slot already filled."""
        from soni.compiler.nodes.collect import CollectNodeFactory
        from soni.config.steps import CollectStepConfig

        step = CollectStepConfig(
            type="collect",
            step="ask_name",
            slot="name",
            message="What is your name?",
        )

        factory = CollectNodeFactory()
        node_fn = factory.create(step)

        mock_context = MagicMock()
        mock_context.flow_manager.get_slot.return_value = "John"  # Already filled
        mock_runtime = MagicMock()
        mock_runtime.context = mock_context

        state = {"flow_stack": [{"flow_id": "test"}], "flow_slots": {}}

        # Should return empty dict - slot already filled
        result = await node_fn(state, mock_runtime)
        assert result == {}

    async def test_collect_node_uses_setslot_command(self):
        """Test that collect node uses SetSlot command when provided by NLU."""
        from soni.compiler.nodes.collect import CollectNodeFactory
        from soni.config.steps import CollectStepConfig
        from soni.flow.manager import FlowDelta

        step = CollectStepConfig(
            type="collect",
            step="ask_name",
            slot="name",
            message="What is your name?",
        )

        factory = CollectNodeFactory()
        node_fn = factory.create(step)

        # Setup: NLU provided SetSlot command
        set_slot_cmd = SetSlot(slot="name", value="Alice", confidence=0.95)

        mock_delta = FlowDelta(flow_slots={"test": {"name": "Alice"}})
        mock_context = MagicMock()
        mock_context.flow_manager.get_slot.return_value = None  # Not filled yet
        mock_context.flow_manager.set_slot.return_value = mock_delta

        mock_runtime = MagicMock()
        mock_runtime.context = mock_context

        state = {
            "flow_stack": [{"flow_id": "test"}],
            "flow_slots": {},
            "commands": [set_slot_cmd],  # NLU provided SetSlot
        }

        # Should use command value, NOT call interrupt()
        result = await node_fn(state, mock_runtime)

        # Verify set_slot was called with command value
        mock_context.flow_manager.set_slot.assert_called_once_with(state, "name", "Alice")

        # Verify waiting flags cleared
        assert result["waiting_for_slot"] is None
        assert result["waiting_for_slot_type"] is None

        # Verify delta merged
        assert result["flow_slots"] == {"test": {"name": "Alice"}}

    async def test_collect_node_uses_dict_command(self):
        """Test that collect node handles dict-format SetSlot commands."""
        from soni.compiler.nodes.collect import CollectNodeFactory
        from soni.config.steps import CollectStepConfig

        step = CollectStepConfig(
            type="collect",
            step="ask_amount",
            slot="amount",
            message="How much?",
        )

        factory = CollectNodeFactory()
        node_fn = factory.create(step)

        # Setup: Command as dict (serialized format)
        mock_context = MagicMock()
        mock_context.flow_manager.get_slot.return_value = None
        mock_context.flow_manager.set_slot.return_value = None

        mock_runtime = MagicMock()
        mock_runtime.context = mock_context

        state = {
            "flow_stack": [{"flow_id": "test"}],
            "flow_slots": {},
            "commands": [{"type": "SetSlot", "slot": "amount", "value": "100 euros"}],
        }

        # Should recognize dict command
        await node_fn(state, mock_runtime)

        # Verify set_slot called
        mock_context.flow_manager.set_slot.assert_called_once_with(state, "amount", "100 euros")

    async def test_collect_node_ignores_wrong_slot_command(self):
        """Test that collect node ignores SetSlot for different slot."""
        from soni.compiler.nodes.collect import CollectNodeFactory
        from soni.config.steps import CollectStepConfig

        step = CollectStepConfig(
            type="collect",
            step="ask_name",
            slot="name",
            message="What is your name?",
        )

        factory = CollectNodeFactory()
        node_fn = factory.create(step)

        # Setup: SetSlot for DIFFERENT slot
        wrong_slot_cmd = SetSlot(slot="age", value="25", confidence=0.9)

        mock_context = MagicMock()
        mock_context.flow_manager.get_slot.return_value = None

        mock_runtime = MagicMock()
        mock_runtime.context = mock_context

        state = {
            "flow_stack": [{"flow_id": "test"}],
            "flow_slots": {},
            "commands": [wrong_slot_cmd],  # Wrong slot!
        }

        # Should NOT use command (would call interrupt(), but we can't test that here)
        # We test this indirectly by verifying set_slot NOT called
        try:
            await node_fn(state, mock_runtime)
        except RuntimeError:
            # Expected - interrupt() called outside runnable context
            pass

        # Verify set_slot was NOT called (command ignored)
        mock_context.flow_manager.set_slot.assert_not_called()
