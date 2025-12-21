import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from soni.actions.handler import ActionHandler
from soni.actions.registry import ActionRegistry


def sync_heavy_action(duration: float):
    """A blocking synchronous action."""
    return {"status": "done"}


class TestSyncActions:
    """Tests for handling synchronous actions safely."""

    @pytest.mark.asyncio
    async def test_executes_sync_action_in_thread(self):
        """Test that sync actions are offloaded to thread."""
        # Arrange
        registry = ActionRegistry()
        # Manually register since instance-level register doesn't exist yet
        registry._actions["heavy_task"] = sync_heavy_action
        handler = ActionHandler(registry)

        with patch("asyncio.to_thread", new_callable=AsyncMock) as mock_to_thread:
            mock_to_thread.return_value = {"status": "done"}

            # Act
            result = await handler.execute("heavy_task", {"duration": 0.01})

            # Assert
            assert result == {"status": "done"}
            mock_to_thread.assert_called_once()
            # Verify called with function and args
            args, kwargs = mock_to_thread.call_args
            assert args[0] == sync_heavy_action
            assert kwargs["duration"] == 0.01

    @pytest.mark.asyncio
    async def test_mixed_async_and_sync_actions(self):
        """Test that both async and sync actions work."""
        # Arrange
        registry = ActionRegistry()

        async def async_action(x):
            return {"val": x}

        def sync_action(x):
            return {"val": x * 2}

        registry._actions["async"] = async_action
        registry._actions["sync"] = sync_action
        handler = ActionHandler(registry)

        # Act
        res1 = await handler.execute("async", {"x": 1})
        # This one typically fails without to_thread if we enforce it,
        # but here we just check it runs.
        # We really want to ensure the sync path uses to_thread.

        with patch("asyncio.to_thread", new_callable=AsyncMock) as mock_to_thread:
            mock_to_thread.return_value = {"val": 4}
            res2 = await handler.execute("sync", {"x": 2})
            mock_to_thread.assert_called_once()

        # Assert
        assert res1 == {"val": 1}
        assert res2 == {"val": 4}
