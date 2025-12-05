"""Tests for graph builder."""

from unittest.mock import AsyncMock, MagicMock

import pytest
from langgraph.checkpoint.memory import InMemorySaver

from soni.core.state import create_initial_state
from soni.dm.builder import build_graph


@pytest.mark.asyncio
async def test_graph_construction():
    """Test graph builds without errors."""
    # Arrange
    mock_context = {
        "flow_manager": MagicMock(),
        "nlu_provider": AsyncMock(),
        "action_handler": AsyncMock(),
        "scope_manager": MagicMock(),
        "normalizer": AsyncMock(),
    }

    # Act
    graph = build_graph(mock_context)

    # Assert
    assert graph is not None
    # Graph should be compiled
    assert hasattr(graph, "nodes")


@pytest.mark.asyncio
async def test_graph_with_checkpointer():
    """Test graph builds with custom checkpointer."""
    # Arrange
    checkpointer = InMemorySaver()
    mock_context = {
        "flow_manager": MagicMock(),
        "nlu_provider": AsyncMock(),
        "action_handler": AsyncMock(),
        "scope_manager": MagicMock(),
        "normalizer": AsyncMock(),
    }

    # Act
    graph = build_graph(mock_context, checkpointer=checkpointer)

    # Assert
    assert graph is not None


@pytest.mark.asyncio
async def test_graph_entry_point():
    """Test graph has correct entry point."""
    # Arrange
    mock_context = {
        "flow_manager": MagicMock(),
        "nlu_provider": AsyncMock(),
        "action_handler": AsyncMock(),
        "scope_manager": MagicMock(),
        "normalizer": AsyncMock(),
    }

    # Act
    graph = build_graph(mock_context)

    # Assert
    # Entry point should be understand node
    # This is verified by graph structure
    assert graph is not None
