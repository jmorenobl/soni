"""Tests for RuntimeLoop dependency injection."""

from unittest.mock import AsyncMock, MagicMock

import pytest
from soni.core.types import DUProtocol
from soni.du.modules import SoniDU
from soni.runtime.loop import RuntimeLoop

from soni.config import SoniConfig


@pytest.fixture
def minimal_config():
    """Create minimal SoniConfig for testing."""
    return SoniConfig(flows={})


class TestRuntimeLoopDI:
    """Tests for RuntimeLoop dependency injection."""

    @pytest.mark.asyncio
    async def test_accepts_custom_du_parameter(self, minimal_config):
        """Test that RuntimeLoop accepts du parameter."""
        # Arrange
        mock_du = MagicMock(spec=DUProtocol)

        # Act - should not raise
        loop = RuntimeLoop(minimal_config, du=mock_du)

        # Assert - check via the initializer
        assert loop._initializer._custom_du is mock_du

    @pytest.mark.asyncio
    async def test_uses_injected_du_after_initialize(self, minimal_config):
        """Test that injected DU is used instead of default."""
        # Arrange
        mock_du = MagicMock(spec=DUProtocol)
        mock_du.aforward = AsyncMock()

        loop = RuntimeLoop(minimal_config, du=mock_du)

        # Act
        await loop.initialize()

        # Assert - use public property
        assert loop.du is mock_du

    @pytest.mark.asyncio
    async def test_creates_default_du_when_not_injected(self, minimal_config):
        """Test that default DU is created when none injected."""
        # Arrange
        loop = RuntimeLoop(minimal_config)

        # Act
        await loop.initialize()

        # Assert - use public property
        assert isinstance(loop.du, SoniDU)
