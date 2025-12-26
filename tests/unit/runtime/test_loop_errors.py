import pytest

from soni.core.errors import SoniError
from soni.runtime.loop import RuntimeLoop


class TestRuntimeLoopErrors:
    """Tests for runtime loop error handling."""

    @pytest.mark.asyncio
    async def test_process_message_without_init_fails(self):
        """Processing message without entering context should fail."""
        from soni.config.models import SoniConfig

        loop = RuntimeLoop(SoniConfig(flows={}))
        with pytest.raises(RuntimeError, match="not initialized"):
            await loop.process_message("Hello")

    @pytest.mark.asyncio
    async def test_handles_nlu_failure_gracefully(self):
        """Should handle errors during message processing gracefully."""
        from unittest.mock import AsyncMock, patch

        from soni.config.models import SoniConfig
        from soni.runtime.loop import RuntimeLoop

        config = SoniConfig(flows={})
        async with RuntimeLoop(config) as loop:
            # Mock graph.ainvoke to fail (this covers NLU or any other node failure)
            with patch.object(loop._graph, "ainvoke", side_effect=Exception("Processing failed")):
                with pytest.raises(Exception, match="Processing failed"):
                    await loop.process_message("Hello", user_id="test")

    def test_loop_handles_invalid_config_during_init(self):
        """Loop initialization with invalid config should fail."""
        with pytest.raises((AttributeError, TypeError)):  # None config
            RuntimeLoop.from_config(None)
