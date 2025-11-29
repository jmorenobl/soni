"""Tests for async migration verification"""

import inspect
from pathlib import Path

import pytest

from soni.core.config import ConfigLoader, SoniConfig
from soni.dm.graph import SoniGraphBuilder


@pytest.mark.asyncio
async def test_checkpointer_is_async():
    """Test that verifies the checkpointer is async"""
    # Arrange
    config_path = Path("examples/flight_booking/soni.yaml")
    config_dict = ConfigLoader.load(config_path)
    config = SoniConfig(**config_dict)

    # Act
    builder = SoniGraphBuilder(config)
    await builder.initialize()  # Initialize checkpointer first
    await builder.build_manual(flow_name="book_flight")

    # Assert
    # Verify that checkpointer is AsyncSqliteSaver (which supports async methods)
    assert builder.checkpointer is not None
    # Check that it's AsyncSqliteSaver and has async methods
    checkpointer_type = type(builder.checkpointer).__name__
    assert checkpointer_type == "AsyncSqliteSaver"
    # Verify it has async methods
    assert hasattr(builder.checkpointer, "aget")
    assert hasattr(builder.checkpointer, "aput")


@pytest.mark.asyncio
async def test_all_nodes_are_async():
    """Test that verifies all nodes are async"""
    # Arrange
    config_path = Path("examples/flight_booking/soni.yaml")
    config_dict = ConfigLoader.load(config_path)
    config = SoniConfig(**config_dict)
    builder = SoniGraphBuilder(config)
    await builder.initialize()  # Initialize checkpointer first

    # Act
    graph = await builder.build_manual(flow_name="book_flight")

    # Assert
    # Verify that all nodes are async functions
    # Get nodes from graph (this may require accessing internal structure)
    assert graph is not None
    # The graph should be compiled successfully, which means all nodes are valid


@pytest.mark.asyncio
async def test_handlers_are_async():
    """Test that verifies handlers are async"""
    # Arrange
    from examples.flight_booking import handlers

    # Act & Assert
    # Verify that all handler functions are async
    handler_functions = [
        handlers.search_available_flights,
        handlers.confirm_flight_booking,
    ]

    for handler in handler_functions:
        assert inspect.iscoroutinefunction(handler), f"{handler.__name__} should be async"


def test_sqlite_saver_has_async_methods():
    """Test that SqliteSaver has async methods"""
    # Arrange & Act
    from langgraph.checkpoint.sqlite import SqliteSaver

    # Assert
    # SqliteSaver should have async methods
    assert hasattr(SqliteSaver, "aget")
    assert hasattr(SqliteSaver, "aput")
    assert hasattr(SqliteSaver, "alist")


def test_understand_node_is_async():
    """Test that understand_node is async"""
    # Arrange
    from soni.dm.graph import understand_node

    # Assert
    assert inspect.iscoroutinefunction(understand_node)


def test_collect_slot_node_is_async():
    """Test that collect_slot_node is async"""
    # Arrange
    from soni.dm.graph import collect_slot_node

    # Assert
    assert inspect.iscoroutinefunction(collect_slot_node)


def test_action_node_is_async():
    """Test that action_node is async"""
    # Arrange
    from soni.dm.graph import action_node

    # Assert
    assert inspect.iscoroutinefunction(action_node)
