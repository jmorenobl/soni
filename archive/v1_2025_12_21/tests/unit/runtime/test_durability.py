"""Tests for durability configuration."""

from unittest.mock import AsyncMock, MagicMock

import pytest


class TestDurabilityConfig:
    """Tests for durability mode configuration."""

    def test_config_accepts_durability_modes(self):
        """Test that SoniConfig accepts valid durability modes."""
        from soni.config import SoniConfig

        for mode in ["sync", "async", "exit"]:
            config = SoniConfig(settings={"durability": mode})
            assert config.settings.durability == mode

    def test_config_default_is_async(self):
        """Test that default durability is async."""
        from soni.config import SoniConfig

        config = SoniConfig()
        assert config.settings.durability == "async"

    def test_config_rejects_invalid_mode(self):
        """Test that SoniConfig rejects invalid durability modes."""
        from soni.config import SoniConfig

        with pytest.raises(ValueError):
            SoniConfig(settings={"durability": "invalid"})


class TestRuntimeLoopDurability:
    """Tests for RuntimeLoop durability passing."""

    @pytest.mark.asyncio
    async def test_passes_durability_to_ainvoke(self):
        """Test that RuntimeLoop passes durability to graph.ainvoke."""
        from soni.runtime.loop import RuntimeLoop

        mock_graph = MagicMock()
        mock_graph.ainvoke = AsyncMock(return_value={"last_response": "ok", "messages": []})
        mock_graph.aget_state = AsyncMock(return_value=MagicMock(values={}))

        mock_config = MagicMock()
        mock_config.settings.durability = "sync"

        loop = RuntimeLoop.__new__(RuntimeLoop)
        loop.config = mock_config
        loop._components = MagicMock()
        loop._components.graph = mock_graph
        loop._components.flow_manager = MagicMock()
        loop._components.action_handler = MagicMock()
        loop._components.du = MagicMock()
        loop._components.slot_extractor = None
        loop._hydrator = MagicMock()
        loop._hydrator.prepare_input.return_value = {"user_message": "hello"}
        loop._extractor = MagicMock()
        loop._extractor.extract.return_value = "ok"

        await loop.process_message("hello")

        # Verify durability was passed
        call_kwargs = mock_graph.ainvoke.call_args.kwargs
        assert call_kwargs.get("durability") == "sync"

    @pytest.mark.asyncio
    async def test_passes_durability_to_astream(self):
        """Test that RuntimeLoop passes durability to graph.astream."""
        from soni.runtime.loop import RuntimeLoop

        mock_graph = MagicMock()
        captured_kwargs = {}

        async def mock_astream(*args, **kwargs):
            # Store kwargs for inspection
            captured_kwargs.update(kwargs)
            yield {"node": {"data": "test"}}

        mock_graph.astream = mock_astream
        mock_graph.aget_state = AsyncMock(return_value=MagicMock(values={}))

        mock_config = MagicMock()
        mock_config.settings.durability = "exit"

        loop = RuntimeLoop.__new__(RuntimeLoop)
        loop.config = mock_config
        loop._components = MagicMock()
        loop._components.graph = mock_graph
        loop._components.flow_manager = MagicMock()
        loop._components.action_handler = MagicMock()
        loop._components.du = MagicMock()
        loop._components.slot_extractor = None
        loop._hydrator = MagicMock()
        loop._hydrator.prepare_input.return_value = {"user_message": "hello"}

        async for _ in loop.process_message_streaming("hello"):
            pass

        # Verify durability was passed
        assert captured_kwargs.get("durability") == "exit"
