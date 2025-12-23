"""Tests for routing functions."""

from typing import Any, cast

import pytest

from soni.core.pending_task import collect
from soni.core.types import DialogueState
from soni.dm.routing import route_after_orchestrator


class TestRouteAfterOrchestrator:
    """Tests for route_after_orchestrator function."""

    def test_returns_pending_task_when_task_exists(self):
        """Test that returns 'pending_task' when _pending_task is set."""
        # Arrange
        state = cast(DialogueState, {"_pending_task": collect(prompt="Test", slot="test")})

        # Act
        result = route_after_orchestrator(state)

        # Assert
        assert result == "pending_task"

    def test_returns_end_when_no_task(self):
        """Test that returns 'end' when _pending_task is None."""
        # Arrange
        state = cast(DialogueState, {"_pending_task": None})

        # Act
        result = route_after_orchestrator(state)

        # Assert
        assert result == "end"

    def test_returns_end_when_task_key_missing(self):
        """Test that returns 'end' when _pending_task key doesn't exist."""
        # Arrange
        state = cast(DialogueState, {})

        # Act
        result = route_after_orchestrator(state)

        # Assert
        assert result == "end"
