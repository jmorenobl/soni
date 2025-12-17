from unittest.mock import AsyncMock, MagicMock

import pytest

from soni.core.config import SoniConfig
from soni.core.types import DUProtocol
from soni.runtime.loop import RuntimeLoop


@pytest.fixture
def minimal_config():
    """Create minimal SoniConfig for testing."""
    return SoniConfig(description="Test config", flows={})


class TestRuntimeLoopDI:
    """Tests for RuntimeLoop dependency injection."""

    @pytest.mark.asyncio
    async def test_accepts_custom_du_parameter(self, minimal_config):
        """Test that RuntimeLoop accepts du parameter."""
        # Arrange
        mock_du = MagicMock(spec=DUProtocol)

        # Act - should not raise
        loop = RuntimeLoop(minimal_config, du=mock_du)

        # Assert
        assert loop._custom_du is mock_du

    @pytest.mark.asyncio
    async def test_uses_injected_du_after_initialize(self, minimal_config):
        """Test that injected DU is used instead of default."""
        # Arrange
        mock_du = MagicMock(spec=DUProtocol)
        mock_du.aforward = AsyncMock()

        loop = RuntimeLoop(minimal_config, du=mock_du)

        # Act
        await loop.initialize()

        # Assert
        # Accessing private attribute _du for verification, or public property if it exists
        # Assuming .du property or _du attribute usage
        assert loop._du is mock_du

    @pytest.mark.asyncio
    async def test_creates_default_du_when_not_injected(self, minimal_config):
        """Test that default DU is created when none injected."""
        # Arrange
        loop = RuntimeLoop(minimal_config)

        # Act
        await loop.initialize()

        # Assert
        from soni.du.modules import SoniDU

        assert isinstance(loop._du, SoniDU)
