from unittest.mock import AsyncMock, MagicMock

import pytest

from soni.core.errors import StateError
from soni.runtime.loop import RuntimeLoop


class TestResetState:
    """Tests for RuntimeLoop.reset_state()."""

    @pytest.fixture
    def mock_config(self):
        """Create mock SoniConfig."""
        config = MagicMock()
        config.settings.persistence.backend = "memory"
        return config

    @pytest.mark.asyncio
    async def test_reset_state_returns_true_when_state_exists(self, mock_config):
        """Test that reset_state returns True when state was cleared."""
        runtime = RuntimeLoop(config=mock_config)
        # Setup: create some state first
        # We need checkpointer mock if we want to really test logic flow without depending on real implementations
        runtime._components = MagicMock()
        checkpointer = MagicMock()
        checkpointer.adelete_thread = AsyncMock(return_value=None)
        runtime._components.checkpointer = checkpointer

        # Mock get_state to return something
        runtime.get_state = AsyncMock(return_value={"some": "state"})  # type: ignore

        # Act
        result = await runtime.reset_state("test_user")

        # Assert
        assert result is True
        # Should call adelete on checkpointer if it supports it, or delete
        # But since we are mocking runtime.reset_state implementation (which doesn't exist yet),
        # this test will fail saying 'RuntimeLoop' object has no attribute 'reset_state'

    @pytest.mark.asyncio
    async def test_reset_state_returns_false_when_no_state(self, mock_config):
        """Test that reset_state returns False when no state existed."""
        runtime = RuntimeLoop(config=mock_config)
        runtime._components = MagicMock()
        runtime._components.checkpointer = MagicMock()

        # Mock get_state to return None
        runtime.get_state = AsyncMock(return_value=None)  # type: ignore

        # Act
        result = await runtime.reset_state("nonexistent_user")

        # Assert
        assert result is False

    @pytest.mark.asyncio
    async def test_reset_state_before_init_returns_false(self, mock_config):
        """Test that reset_state returns False if called before init (components None)."""
        runtime = RuntimeLoop(config=mock_config)
        # Don't initialize components
        runtime._components = None

        result = await runtime.reset_state("test_user")

        assert result is False

    @pytest.mark.asyncio
    async def test_reset_state_with_checkpointer_error_raises(self, mock_config):
        """Test that checkpointer errors are propagated as StateError."""
        runtime = RuntimeLoop(config=mock_config)
        runtime._components = MagicMock()
        runtime._components.checkpointer = MagicMock()
        runtime.get_state = AsyncMock(return_value={"some": "state"})  # type: ignore

        # Mock checkpointer to look real
        checkpointer = MagicMock()
        # When accessing adelete, return an AsyncMock that raises
        checkpointer.adelete_thread = AsyncMock(side_effect=Exception("DB connection lost"))
        # We also need 'adelete' to be present in dir/hasattr? MagicMock handles that.
        # But we ensure delete is NOT present or logic will try that first if precedence...
        # Actually logic is 'if hasattr adelete await adelete'.
        # The issue 'object MagicMock can't be used in await' means logic might have accessed checkpointer itself?
        # Or 'adelete' mock was wrapped weirdly.
        # Let's try explicitly setting spec=None to avoid auto-speccing issues if any.

        runtime._components.checkpointer = checkpointer

        with pytest.raises(StateError) as exc_info:
            await runtime.reset_state("test_user")

        assert "Reset failed" in str(exc_info.value)
