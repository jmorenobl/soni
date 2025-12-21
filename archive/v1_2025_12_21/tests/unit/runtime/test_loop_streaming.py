"""Tests for RuntimeLoop streaming functionality."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest


class TestRuntimeLoopStreaming:
    """Tests for process_message_streaming method."""

    @pytest.fixture
    def mock_graph(self):
        """Create mock compiled graph with astream."""
        graph = MagicMock()
        graph.astream = AsyncMock()
        return graph

    @pytest.fixture
    def runtime_loop(self, mock_graph):
        """Create RuntimeLoop with mocked graph."""
        from soni.runtime.initializer import RuntimeComponents
        from soni.runtime.loop import RuntimeLoop

        loop = RuntimeLoop.__new__(RuntimeLoop)
        loop._components = MagicMock(spec=RuntimeComponents)
        loop._components.graph = mock_graph
        loop._components.flow_manager = MagicMock()
        loop._components.action_handler = MagicMock()
        loop._components.du = MagicMock()
        loop._components.slot_extractor = None
        loop._hydrator = MagicMock()
        loop._hydrator.prepare_input.return_value = {"user_message": "test"}
        loop.config = MagicMock()
        return loop

    @pytest.mark.asyncio
    async def test_process_message_streaming_yields_chunks(self, runtime_loop, mock_graph):
        """Test that streaming yields chunks from graph.astream()."""
        # Arrange
        expected_chunks = [
            {"understand": {"nlu_result": "parsed"}},
            {"respond": {"last_response": "Hello!"}},
        ]

        async def mock_astream(*args, **kwargs):
            for chunk in expected_chunks:
                yield chunk

        mock_graph.astream = mock_astream

        with patch.object(runtime_loop, "get_state", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = None

            # Act
            chunks = []
            async for chunk in runtime_loop.process_message_streaming("Hi"):
                chunks.append(chunk)

        # Assert
        assert chunks == expected_chunks

    @pytest.mark.asyncio
    async def test_process_message_streaming_uses_updates_mode_by_default(
        self, runtime_loop, mock_graph
    ):
        """Test that default stream_mode is 'updates'."""
        # Arrange
        captured_kwargs = {}

        async def mock_astream(*args, **kwargs):
            captured_kwargs.update(kwargs)
            yield {"node": {"data": "test"}}

        mock_graph.astream = mock_astream

        with patch.object(runtime_loop, "get_state", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = None

            # Act
            async for _ in runtime_loop.process_message_streaming("test"):
                pass

        # Assert
        assert captured_kwargs.get("stream_mode") == "updates"

    @pytest.mark.asyncio
    async def test_process_message_streaming_accepts_custom_stream_mode(
        self, runtime_loop, mock_graph
    ):
        """Test that custom stream_mode is passed to graph."""
        # Arrange
        captured_kwargs = {}

        async def mock_astream(*args, **kwargs):
            captured_kwargs.update(kwargs)
            yield {"state": "full"}

        mock_graph.astream = mock_astream

        with patch.object(runtime_loop, "get_state", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = None

            # Act
            async for _ in runtime_loop.process_message_streaming("test", stream_mode="values"):
                pass

        # Assert
        assert captured_kwargs.get("stream_mode") == "values"

    @pytest.mark.asyncio
    async def test_process_message_streaming_includes_runtime_context(
        self, runtime_loop, mock_graph
    ):
        """Test that RuntimeContext is included in config."""
        # Arrange
        captured_config = {}

        captured_kwargs = {}

        async def mock_astream(*args, **kwargs):
            captured_kwargs.update(kwargs)
            captured_config.update(kwargs.get("config", {}))
            yield {"node": {}}

        mock_graph.astream = mock_astream

        with patch.object(runtime_loop, "get_state", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = None

            # Act
            async for _ in runtime_loop.process_message_streaming("test", user_id="user1"):
                pass

        # Assert
        assert "configurable" in captured_config
        assert "thread_id" in captured_config["configurable"]

        # Verify context injection
        assert "context" in captured_kwargs
        from soni.core.types import RuntimeContext

        assert isinstance(captured_kwargs["context"], RuntimeContext)
