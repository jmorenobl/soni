"""Tests for RuntimeLoop and FastAPI lifespan cleanup functionality."""

import logging
from unittest.mock import AsyncMock, MagicMock

import pytest


class TestRuntimeLoopCleanup:
    """Tests for RuntimeLoop cleanup functionality."""

    @pytest.fixture
    def mock_config(self):
        config = MagicMock()
        config.settings.persistence.backend = "memory"
        return config

    @pytest.mark.asyncio
    async def test_cleanup_closes_checkpointer(self, mock_config):
        """Test that cleanup closes the checkpointer."""
        from soni.runtime.loop import RuntimeLoop

        runtime = RuntimeLoop(config=mock_config)
        await runtime.initialize()

        # Mock checkpointer with aclose
        assert runtime._components is not None  # For mypy
        mock_checkpointer = MagicMock()
        mock_checkpointer.aclose = AsyncMock()
        runtime._components.checkpointer = mock_checkpointer

        await runtime.cleanup()

        mock_checkpointer.aclose.assert_called_once()

    @pytest.mark.asyncio
    async def test_cleanup_handles_sync_close(self, mock_config):
        """Test that cleanup handles sync close method."""
        from soni.runtime.loop import RuntimeLoop

        runtime = RuntimeLoop(config=mock_config)
        await runtime.initialize()

        # Mock checkpointer with only sync close
        assert runtime._components is not None  # For mypy
        mock_checkpointer = MagicMock(spec=["close"])
        mock_checkpointer.close = MagicMock()
        runtime._components.checkpointer = mock_checkpointer

        await runtime.cleanup()

        mock_checkpointer.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_cleanup_handles_no_checkpointer(self, mock_config):
        """Test that cleanup handles missing checkpointer gracefully."""
        from soni.runtime.loop import RuntimeLoop

        runtime = RuntimeLoop(config=mock_config)
        await runtime.initialize()

        # Remove checkpointer
        assert runtime._components is not None  # For mypy
        runtime._components.checkpointer = None

        # Should not raise
        await runtime.cleanup()

    @pytest.mark.asyncio
    async def test_cleanup_clears_components(self, mock_config):
        """Test that cleanup clears component references."""
        from soni.runtime.loop import RuntimeLoop

        runtime = RuntimeLoop(config=mock_config)
        await runtime.initialize()

        assert runtime._components is not None

        await runtime.cleanup()

        assert runtime._components is None

    @pytest.mark.asyncio
    async def test_cleanup_before_init_is_safe(self, mock_config):
        """Test that cleanup before initialization doesn't fail."""
        from soni.runtime.loop import RuntimeLoop

        runtime = RuntimeLoop(config=mock_config)
        # Don't initialize

        # Should not raise
        await runtime.cleanup()

    @pytest.mark.asyncio
    async def test_cleanup_handles_checkpointer_error(self, mock_config, caplog):
        """Test that cleanup handles checkpointer close errors gracefully."""
        from soni.runtime.loop import RuntimeLoop

        runtime = RuntimeLoop(config=mock_config)
        await runtime.initialize()

        # Mock checkpointer that raises on close
        assert runtime._components is not None  # For mypy
        mock_checkpointer = MagicMock()
        mock_checkpointer.aclose = AsyncMock(side_effect=Exception("Close failed"))
        runtime._components.checkpointer = mock_checkpointer

        with caplog.at_level(logging.WARNING):
            await runtime.cleanup()  # Should not raise

        assert "Error closing checkpointer" in caplog.text


class TestLifespanCleanup:
    """Tests for FastAPI lifespan cleanup."""

    @pytest.mark.asyncio
    async def test_lifespan_calls_runtime_cleanup(self):
        """Test that lifespan uses RuntimeLoop context manager."""
        from unittest.mock import patch

        from soni.server.api import app, lifespan

        mock_runtime = MagicMock()
        mock_runtime.initialize = AsyncMock()
        mock_runtime.cleanup = AsyncMock()
        # Mock context manager behavior
        mock_runtime.__aenter__ = AsyncMock(return_value=mock_runtime)
        mock_runtime.__aexit__ = AsyncMock(return_value=False)

        # Mock config loader and Path existence
        with (
            patch("soni.server.api.ConfigLoader.load", return_value=MagicMock()),
            patch("soni.server.api.RuntimeLoop", return_value=mock_runtime),
            patch("pathlib.Path.exists", return_value=True),
        ):
            async with lifespan(app):
                # Verify initialization happened upon entry
                mock_runtime.__aenter__.assert_called_once()
                assert app.state.runtime is mock_runtime

            # Verify cleanup happened upon exit
            mock_runtime.__aexit__.assert_called_once()
