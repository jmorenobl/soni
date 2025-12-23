"""Tests for migrated subgraph nodes using PendingTask."""

from typing import Any, cast
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from soni.core.pending_task import is_collect, is_confirm, is_inform
from soni.core.types import DialogueState


def mock_interpolate(text, state):
    """Simple mock for interpolate."""
    if not isinstance(text, str):
        return text
    if not state or "flow_slots" not in state:
        return text
    try:
        return text.format(**state.get("flow_slots", {}))
    except (KeyError, ValueError):
        return text


class TestCollectNode:
    """Tests for collect_node returning PendingTask."""

    @pytest.mark.asyncio
    async def test_collect_returns_pending_task_when_slot_empty(self):
        """Test that collect_node returns CollectTask when slot is empty."""
        # Arrange
        from soni.compiler.nodes.collect import collect_node

        config = MagicMock()
        config.slot = "amount"
        config.message = "Enter amount:"

        state: dict[str, Any] = {
            "flow_slots": {},  # Empty slots
            "user_message": None,
        }
        runtime = MagicMock()
        runtime.context.flow_manager.get_slot.return_value = None

        # Act
        result = await collect_node(cast(DialogueState, state), runtime, config)

        # Assert
        assert "_pending_task" in result
        task = result["_pending_task"]
        assert is_collect(task)
        assert task["slot"] == "amount"
        assert task["prompt"] == "Enter amount:"

    @pytest.mark.asyncio
    async def test_collect_returns_empty_when_slot_filled(self):
        """Test that collect_node returns empty dict when slot has value."""
        # Arrange
        from soni.compiler.nodes.collect import collect_node

        config = MagicMock()
        config.slot = "amount"

        state: dict[str, Any] = {
            "flow_slots": {"amount": "500"},  # Slot has value
        }
        runtime = MagicMock()

        # Act
        result = await collect_node(cast(DialogueState, state), runtime, config)

        # Assert
        assert "_pending_task" not in result or result.get("_pending_task") is None

    @pytest.mark.asyncio
    async def test_collect_does_not_call_interrupt(self):
        """Test that collect_node does NOT call interrupt() directly."""
        # Arrange
        from soni.compiler.nodes.collect import collect_node

        config = MagicMock()
        config.slot = "amount"
        config.message = "Enter amount:"

        # Act
        with patch("soni.compiler.nodes.collect.interpolate", side_effect=mock_interpolate):
            try:
                import soni.compiler.nodes.collect as collect_module

                if hasattr(collect_module, "interrupt"):
                    pytest.fail("interrupt should not be in collect.py")
            except AttributeError:
                pass


class TestConfirmNode:
    """Tests for confirm_node returning PendingTask."""

    @pytest.mark.asyncio
    async def test_confirm_returns_pending_task_when_unconfirmed(self):
        """Test that confirm_node returns ConfirmTask when not confirmed."""
        # Arrange
        from soni.compiler.nodes.confirm import confirm_node

        config = MagicMock()
        config.message = "Proceed with transfer?"

        state: dict[str, Any] = {
            "flow_slots": {"amount": "500", "destination": "savings"},
            "_confirmed": False,
        }
        runtime = MagicMock()

        # Act
        result = await confirm_node(cast(DialogueState, state), runtime, config)

        # Assert
        assert "_pending_task" in result
        task = result["_pending_task"]
        assert is_confirm(task)
        assert "Proceed" in task["prompt"] or task["prompt"] == config.message

    @pytest.mark.asyncio
    async def test_confirm_returns_empty_when_already_confirmed(self):
        """Test that confirm_node returns empty when already confirmed."""
        # Arrange
        from soni.compiler.nodes.confirm import confirm_node

        config = MagicMock()
        state: dict[str, Any] = {"_confirmed": True}
        runtime = MagicMock()

        # Act
        result = await confirm_node(cast(DialogueState, state), runtime, config)

        # Assert
        assert "_pending_task" not in result or result.get("_pending_task") is None


class TestActionNode:
    """Tests for action_node returning InformTask."""

    @pytest.mark.asyncio
    async def test_action_returns_inform_task_with_result(self):
        """Test that action_node returns InformTask with action result."""
        # Arrange
        from soni.compiler.nodes.action import action_node

        config = MagicMock()
        config.action_name = "check_balance"

        mock_action_result = MagicMock()
        mock_action_result.message = "Your balance is $1,234"

        state: dict[str, Any] = {"flow_slots": {"account": "checking"}}
        runtime = MagicMock()
        runtime.context.action_registry.execute = AsyncMock(return_value=mock_action_result)

        # Act
        result = await action_node(cast(DialogueState, state), runtime, config)

        # Assert
        assert "_pending_task" in result
        task = result["_pending_task"]
        assert is_inform(task)
        # Use a more flexible check for prompt
        assert "Your balance is $1,234" in task["prompt"]

    @pytest.mark.asyncio
    async def test_action_inform_does_not_wait_by_default(self):
        """Test that action result InformTask does not wait for ack by default."""
        # Arrange
        from soni.compiler.nodes.action import action_node

        config = MagicMock()
        mock_result = MagicMock()
        mock_result.message = "Done"

        state: dict[str, Any] = {}
        runtime = MagicMock()
        runtime.context.action_registry.execute = AsyncMock(return_value=mock_result)

        # Act
        result = await action_node(cast(DialogueState, state), runtime, config)

        # Assert
        task = result["_pending_task"]
        assert task.get("wait_for_ack") is not True

    @pytest.mark.asyncio
    async def test_action_silent_with_dict_result_and_no_wait(self):
        """Test that action returning simple dict without wait_for_ack is silent."""
        # Arrange
        from soni.compiler.nodes.action import action_node

        config = MagicMock()
        config.wait_for_ack = False
        config.call = "silent_action"

        # Result is a raw dict without "message" key
        mock_result = {"key": "value", "id": 123}

        state: dict[str, Any] = {}
        runtime = MagicMock()
        runtime.context.action_registry.execute = AsyncMock(return_value=mock_result)

        # Act
        result = await action_node(cast(DialogueState, state), runtime, config)

        # Assert
        # Should NOT have _pending_task
        assert "_pending_task" not in result or result.get("_pending_task") is None

    @pytest.mark.asyncio
    async def test_action_output_string_is_displayed(self):
        """Test that action returning a string message is displayed."""
        # Arrange
        from soni.compiler.nodes.action import action_node

        config = MagicMock()
        config.wait_for_ack = False
        config.call = "get_balance"

        # Result is a simple string message
        mock_result = "Your balance is $1,000"

        state: dict[str, Any] = {}
        runtime = MagicMock()
        runtime.context.action_registry.execute = AsyncMock(return_value=mock_result)

        # Act
        result = await action_node(cast(DialogueState, state), runtime, config)

        # Assert
        # Should have _pending_task because it IS a message
        assert "_pending_task" in result
        task = result["_pending_task"]
        assert is_inform(task)
        assert task["prompt"] == "Your balance is $1,000"
