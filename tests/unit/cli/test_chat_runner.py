"""Tests for ChatRunner class."""

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from soni.cli.chat_runner import ChatConfig, ChatRunner


class TestChatRunner:
    """Tests for ChatRunner."""

    @pytest.fixture
    def config(self, tmp_path):
        """Create test config."""
        return ChatConfig(
            config_path=tmp_path / "soni.yaml",
            verbose=False,
            debug=False,
        )

    @pytest.mark.asyncio
    async def test_init_stores_config(self, config):
        """Test that config is stored correctly."""
        runner = ChatRunner(config)
        assert runner.config == config
        assert runner.runtime is None

    @pytest.mark.asyncio
    async def test_setup_initializes_runtime(self, config):
        """Test that setup initializes runtime."""
        with patch("soni.cli.chat_runner.ConfigLoader.load") as mock_load:
            with patch("soni.cli.chat_runner.RuntimeLoop") as mock_runtime:
                mock_runtime.return_value.__aenter__ = AsyncMock()
                mock_load.return_value = MagicMock()
                runner = ChatRunner(config)
                await runner.setup()
                assert runner.runtime is not None
                mock_runtime.assert_called_once()

    @pytest.mark.asyncio
    async def test_cleanup_releases_resources(self, config):
        """Test that cleanup releases resources."""
        runner = ChatRunner(config)
        runner.runtime = AsyncMock()
        await runner.cleanup()
        assert runner.runtime is None

    def test_is_exit_command_recognizes_quit(self, config):
        """Test exit command recognition."""
        runner = ChatRunner(config)
        assert runner._is_exit_command("quit")
        assert runner._is_exit_command("exit")
        assert runner._is_exit_command("q")
        assert runner._is_exit_command("/quit")
        assert not runner._is_exit_command("hello")

    @pytest.mark.asyncio
    async def test_context_manager_calls_setup_and_cleanup(self, config):
        """Test async context manager protocol."""
        with patch.object(ChatRunner, "setup", new_callable=AsyncMock) as mock_setup:
            with patch.object(ChatRunner, "cleanup", new_callable=AsyncMock) as mock_cleanup:
                async with ChatRunner(config):
                    pass
                mock_setup.assert_called_once()
                mock_cleanup.assert_called_once()
