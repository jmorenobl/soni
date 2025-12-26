"""Tests for human_input_gate node."""

from typing import cast
from unittest.mock import patch

import pytest

from soni.core.types import DialogueState
from soni.dm.nodes.human_input_gate import human_input_gate


class TestHumanInputGate:
    """Tests for human_input_gate node function."""

    @pytest.mark.asyncio
    async def test_returns_empty_when_no_pending_task(self):
        """Test that gate returns empty dict when no pending task."""
        # Arrange
        state = {"user_message": "Hello", "_pending_task": None}

        # Act
        result = await human_input_gate(cast(DialogueState, state))

        # Assert
        assert result == {}

    @pytest.mark.asyncio
    async def test_returns_empty_when_pending_task_key_missing(self):
        """Test that gate returns empty dict when key doesn't exist."""
        # Arrange
        state = {"user_message": "Hello"}

        # Act
        result = await human_input_gate(cast(DialogueState, state))

        # Assert
        assert result == {}


class TestHumanInputGateWithPendingTask:
    """Tests for human_input_gate with pending tasks."""

    def test_gate_is_async_function(self):
        """Test that human_input_gate is an async function."""
        # Arrange & Act & Assert
        import inspect

        try:
            from soni.dm.nodes.human_input_gate import human_input_gate

            assert inspect.iscoroutinefunction(human_input_gate)
        except ImportError:
            pytest.fail("human_input_gate not implemented yet")

    def test_gate_accepts_only_state(self):
        """Test that human_input_gate signature only requires state."""
        # Arrange & Act
        import inspect

        try:
            from soni.dm.nodes.human_input_gate import human_input_gate

            sig = inspect.signature(human_input_gate)

            # Assert - only one required parameter
            required_params = [
                p for p in sig.parameters.values() if p.default == inspect.Parameter.empty
            ]
            assert len(required_params) == 1
            assert "state" in sig.parameters
        except ImportError:
            pytest.fail("human_input_gate not implemented yet")
