"""Tests for RuntimeLoop async context manager protocol.

Verifies proper resource management via __aenter__/__aexit__.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from soni.runtime.loop import RuntimeLoop


@pytest.fixture
def mock_config() -> MagicMock:
    """Create mock SoniConfig."""
    config = MagicMock()
    config.flows = {}
    config.slots = {}
    return config


class TestAsyncContextManagerProtocol:
    """Tests for __aenter__ and __aexit__ implementation."""

    @pytest.mark.asyncio
    async def test_aenter_initializes_runtime(self, mock_config: MagicMock) -> None:
        """Test that __aenter__ calls initialize()."""
        runtime = RuntimeLoop(mock_config)

        # We can't use 'new_callable=AsyncMock' directly on runtim.initialize if it's not async in class definition yet
        # But initialize IS async already.
        with patch.object(runtime, "initialize", new_callable=AsyncMock) as mock_init:
            result = await runtime.__aenter__()

            mock_init.assert_called_once()
            assert result is runtime

    @pytest.mark.asyncio
    async def test_aexit_calls_cleanup(self, mock_config: MagicMock) -> None:
        """Test that __aexit__ calls cleanup()."""
        runtime = RuntimeLoop(mock_config)

        # Inject mock components locally since we don't call initialize
        runtime._components = MagicMock()

        with patch.object(runtime, "cleanup", new_callable=AsyncMock) as mock_cleanup:
            result = await runtime.__aexit__(None, None, None)

            mock_cleanup.assert_called_once()
            assert result is False  # Should not suppress exceptions

    @pytest.mark.asyncio
    async def test_aexit_calls_cleanup_on_exception(self, mock_config: MagicMock) -> None:
        """Test that __aexit__ calls cleanup even when exception occurred."""
        runtime = RuntimeLoop(mock_config)
        runtime._components = MagicMock()

        with patch.object(runtime, "cleanup", new_callable=AsyncMock) as mock_cleanup:
            result = await runtime.__aexit__(ValueError, ValueError("test error"), None)

            mock_cleanup.assert_called_once()
            assert result is False  # Should propagate exception

    @pytest.mark.asyncio
    async def test_context_manager_usage(self, mock_config: MagicMock) -> None:
        """Test RuntimeLoop can be used as async context manager."""
        with (
            patch.object(RuntimeLoop, "initialize", new_callable=AsyncMock) as mock_init,
            patch.object(RuntimeLoop, "cleanup", new_callable=AsyncMock) as mock_cleanup,
        ):
            async with RuntimeLoop(mock_config) as runtime:
                assert runtime is not None
                mock_init.assert_called_once()

            mock_cleanup.assert_called_once()


class TestContextManagerCleanup:
    """Tests for cleanup behavior in context manager."""

    @pytest.mark.asyncio
    async def test_cleanup_on_normal_exit(self, mock_config: MagicMock) -> None:
        """Test resources are cleaned up on normal context exit."""
        cleanup_called = False

        async def track_cleanup() -> None:
            nonlocal cleanup_called
            cleanup_called = True

        runtime = RuntimeLoop(mock_config)

        with (
            patch.object(runtime, "initialize", new_callable=AsyncMock),
            patch.object(runtime, "cleanup", side_effect=track_cleanup),
        ):
            async with runtime:
                assert not cleanup_called

            assert cleanup_called

    @pytest.mark.asyncio
    async def test_cleanup_on_exception(self, mock_config: MagicMock) -> None:
        """Test resources are cleaned up when exception raised inside context."""
        cleanup_called = False

        async def track_cleanup() -> None:
            nonlocal cleanup_called
            cleanup_called = True

        runtime = RuntimeLoop(mock_config)

        with (
            patch.object(runtime, "initialize", new_callable=AsyncMock),
            patch.object(runtime, "cleanup", side_effect=track_cleanup),
        ):
            with pytest.raises(ValueError, match="intentional"):
                async with runtime:
                    raise ValueError("intentional error")

            assert cleanup_called

    @pytest.mark.asyncio
    async def test_exception_propagates(self, mock_config: MagicMock) -> None:
        """Test that exceptions inside context are propagated."""
        runtime = RuntimeLoop(mock_config)

        with (
            patch.object(runtime, "initialize", new_callable=AsyncMock),
            patch.object(runtime, "cleanup", new_callable=AsyncMock),
        ):
            with pytest.raises(RuntimeError, match="test error"):
                async with runtime:
                    raise RuntimeError("test error")


class TestCleanupIdempotency:
    """Tests for idempotent cleanup behavior."""

    @pytest.mark.asyncio
    async def test_cleanup_can_be_called_multiple_times(self, mock_config: MagicMock) -> None:
        """Test cleanup() is safe to call multiple times."""
        runtime = RuntimeLoop(mock_config)
        runtime._components = MagicMock()
        runtime._components.checkpointer = None

        # First cleanup
        await runtime.cleanup()
        assert runtime._components is None
        assert runtime._cleanup_done is True

        # Second cleanup should be no-op
        await runtime.cleanup()  # Should not raise

    @pytest.mark.asyncio
    async def test_cleanup_flag_prevents_double_cleanup(self, mock_config: MagicMock) -> None:
        """Test _cleanup_done flag prevents redundant cleanup."""
        mock_checkpointer = MagicMock()
        mock_checkpointer.aclose = AsyncMock()

        runtime = RuntimeLoop(mock_config, checkpointer=mock_checkpointer)
        runtime._components = MagicMock()
        runtime._components.checkpointer = mock_checkpointer

        await runtime.cleanup()
        await runtime.cleanup()  # Second call

        # aclose should only be called once
        assert mock_checkpointer.aclose.call_count == 1


class TestIntegrationScenarios:
    """Tests for real-world usage scenarios."""

    @pytest.mark.asyncio
    async def test_multiple_requests_within_context(self, mock_config: MagicMock) -> None:
        """Test multiple process_message calls work within context."""
        runtime = RuntimeLoop(mock_config)

        with (
            patch.object(runtime, "initialize", new_callable=AsyncMock),
            patch.object(runtime, "cleanup", new_callable=AsyncMock),
            patch.object(
                runtime, "process_message", new_callable=AsyncMock, return_value="response"
            ) as mock_process,
        ):
            async with runtime:
                await runtime.process_message("msg1", "user1")
                await runtime.process_message("msg2", "user2")
                await runtime.process_message("msg3", "user1")

            assert mock_process.call_count == 3

    @pytest.mark.asyncio
    async def test_cleanup_releases_checkpointer(self, mock_config: MagicMock) -> None:
        """Test checkpointer is properly closed during cleanup."""
        mock_checkpointer = MagicMock()
        mock_checkpointer.aclose = AsyncMock()

        runtime = RuntimeLoop(mock_config, checkpointer=mock_checkpointer)

        # Simulate initialized state
        runtime._components = MagicMock()
        runtime._components.checkpointer = mock_checkpointer

        await runtime.cleanup()

        mock_checkpointer.aclose.assert_called_once()
