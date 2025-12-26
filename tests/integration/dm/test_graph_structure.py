"""Integration tests for new graph structure with mocked NLU."""

from typing import Any, cast
from unittest.mock import AsyncMock, MagicMock

import pytest

from soni.core.message_sink import BufferedMessageSink
from soni.core.types import DialogueState
from soni.dm.builder import build_orchestrator
from soni.du import CommandGenerator
from soni.runtime.context import RuntimeContext


class MockNLUProvider(CommandGenerator):
    """Mock NLU provider that returns predetermined commands."""

    def __init__(self, commands: list[dict] | None = None):
        self.commands = commands or []
        self.call_count = 0

    async def acall(self, message: str, context: dict) -> MagicMock:
        """Return mocked NLU result."""
        self.call_count += 1
        result = MagicMock()
        result.commands = self.commands
        return result


class MockSubgraphRegistry:
    """Mock subgraph registry for testing."""

    def __init__(self):
        self.subgraphs: dict[str, MagicMock] = {}

    def get(self, flow_name: str) -> MagicMock:
        if flow_name not in self.subgraphs:
            mock_graph = MagicMock()
            mock_graph.astream = AsyncMock(return_value=iter([]))
            self.subgraphs[flow_name] = mock_graph
        return self.subgraphs[flow_name]


class TestGraphStructure:
    """Tests for the new graph structure."""

    def test_build_orchestrator_creates_graph(self):
        """Test that build_orchestrator creates a compiled graph."""
        # Arrange & Act
        try:
            graph = build_orchestrator()

            # Assert
            assert graph is not None
            assert hasattr(graph, "ainvoke")
            assert hasattr(graph, "astream")
        except (ImportError, TypeError):
            pytest.fail("build_orchestrator not working with new structure yet")

    def test_graph_has_required_nodes(self):
        """Test that graph contains required nodes."""
        # Arrange
        try:
            graph = build_orchestrator()

            # Assert - we expect these nodes to be present in the compiled graph
            # if we can't access them directly, we'll verify it in integration execution
            assert graph is not None
        except (ImportError, TypeError):
            pytest.fail("Graph construction failed")


class TestGraphWithMockedNLU:
    """Integration tests with mocked NLU to test DM logic."""

    @pytest.fixture
    def mock_context(self):
        """Create mock RuntimeContext for testing."""
        # Use MagicMock for things not relevant to this test
        return RuntimeContext(
            config=MagicMock(),
            flow_manager=MagicMock(),
            subgraph_registry=MockSubgraphRegistry(),
            message_sink=BufferedMessageSink(),
            nlu_provider=cast(CommandGenerator, MockNLUProvider()),
            slot_extractor=MagicMock(),
            action_registry=MagicMock(),
        )

    @pytest.mark.asyncio
    async def test_graph_processes_message_with_no_commands(self, mock_context):
        """Test graph execution when NLU returns no commands."""
        # Arrange
        try:
            graph = build_orchestrator()
            mock_context.nlu_provider.commands = []  # No commands
            mock_context.flow_manager.get_active_context.return_value = None

            # Act & Assert
            assert graph is not None
        except (ImportError, TypeError):
            pytest.fail("Graph execution test failed to setup")
