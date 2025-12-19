"""Tests for reset_state using correct LangGraph API."""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from soni.runtime.loop import RuntimeLoop


class MockAsyncCheckpointer:
    """Mock checkpointer with correct LangGraph async API."""

    def __init__(self):
        self.adelete_thread_called = False
        self.last_deleted_thread_id: str | None = None

    async def adelete_thread(self, thread_id: str) -> None:
        """Async delete_thread - correct LangGraph API."""
        await asyncio.sleep(0.01)
        self.adelete_thread_called = True
        self.last_deleted_thread_id = thread_id

    async def aclose(self) -> None:
        """Async close."""
        await asyncio.sleep(0.01)


@pytest.fixture
def mock_config() -> MagicMock:
    """Create mock SoniConfig."""
    config = MagicMock()
    config.flows = {}
    config.slots = {}
    return config


class TestResetStateCorrectAPI:
    """Tests for reset_state using correct LangGraph API."""

    @pytest.mark.asyncio
    async def test_reset_state_calls_adelete_thread_with_user_id(
        self, mock_config: MagicMock
    ) -> None:
        """Test that adelete_thread is called with thread_id directly."""
        async_checkpointer = MockAsyncCheckpointer()

        runtime = RuntimeLoop(mock_config, checkpointer=async_checkpointer)
        runtime._components = MagicMock()
        runtime._components.checkpointer = async_checkpointer
        runtime._components.graph = MagicMock()

        with patch.object(runtime, "get_state", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = {"some": "state"}

            await runtime.reset_state("user_123")

            assert async_checkpointer.adelete_thread_called
            assert async_checkpointer.last_deleted_thread_id == "user_123"

    @pytest.mark.asyncio
    async def test_reset_state_does_not_use_old_api(self, mock_config: MagicMock) -> None:
        """Verify we don't call the old incorrect adelete method."""
        async_checkpointer = MockAsyncCheckpointer()
        # Add the old incorrect method to verify it's NOT called
        async_checkpointer.adelete = AsyncMock()  # type: ignore

        runtime = RuntimeLoop(mock_config, checkpointer=async_checkpointer)
        runtime._components = MagicMock()
        runtime._components.checkpointer = async_checkpointer
        runtime._components.graph = MagicMock()

        with patch.object(runtime, "get_state", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = {"some": "state"}

            await runtime.reset_state("user_123")

            # Old method should NOT be called
            async_checkpointer.adelete.assert_not_called()  # type: ignore
            # Correct method should be called
            assert async_checkpointer.adelete_thread_called

    @pytest.mark.asyncio
    async def test_reset_state_fallback_to_empty_state(self, mock_config: MagicMock) -> None:
        """Test fallback when checkpointer has no adelete_thread."""
        # Checkpointer without adelete_thread method
        basic_checkpointer = MagicMock()
        del basic_checkpointer.adelete_thread  # Ensure it doesn't exist

        runtime = RuntimeLoop(mock_config, checkpointer=basic_checkpointer)
        runtime._components = MagicMock()
        runtime._components.checkpointer = basic_checkpointer
        mock_graph = MagicMock()
        mock_graph.aupdate_state = AsyncMock()
        runtime._components.graph = mock_graph

        with patch.object(runtime, "get_state", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = {"some": "state"}

            result = await runtime.reset_state("user_123")

            assert result is True
            mock_graph.aupdate_state.assert_called_once()
