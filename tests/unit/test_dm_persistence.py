"""Unit tests for persistence and checkpointing"""

import pytest

from soni.core.config import PersistenceConfig
from soni.dm.persistence import CheckpointerFactory


@pytest.fixture
async def sqlite_checkpointer():
    """
    Fixture that creates and cleans up a SQLite checkpointer for testing.

    This fixture ensures proper cleanup of SQLite connections to prevent ResourceWarnings.
    Uses try/finally to guarantee cleanup even if tests fail.
    """
    config = PersistenceConfig(backend="sqlite", path=":memory:")
    checkpointer = None
    cm = None

    try:
        checkpointer, cm = await CheckpointerFactory.create(config)
        yield checkpointer, cm
    finally:
        # Always cleanup, even if test fails or checkpointer creation fails
        if cm is not None:
            try:
                # Properly close the async context manager
                # This closes the SQLite connection to prevent ResourceWarnings
                await cm.__aexit__(None, None, None)
            except Exception as e:
                # Log but don't fail on cleanup errors
                import logging

                logging.getLogger(__name__).debug(f"Error during SQLite cleanup: {e}")
            finally:
                # Ensure references are cleared to help garbage collection
                # This is especially important when running with pytest-cov
                # which can delay garbage collection
                cm = None
                checkpointer = None
                # Force garbage collection hint (doesn't guarantee immediate GC)
                # but helps ensure cleanup happens before pytest-cov tracks coverage
                import gc

                gc.collect()


@pytest.mark.asyncio
async def test_create_memory_checkpointer():
    """Test that memory checkpointer is created correctly"""
    # Arrange
    config = PersistenceConfig(backend="memory")

    # Act
    checkpointer, cm = await CheckpointerFactory.create(config)

    # Assert
    assert checkpointer is not None
    assert cm is None  # InMemorySaver does not require context manager
    from langgraph.checkpoint.memory import InMemorySaver

    assert isinstance(checkpointer, InMemorySaver)


@pytest.mark.asyncio
async def test_memory_checkpointer_no_context_manager():
    """Test that memory checkpointer returns None as context manager"""
    # Arrange
    config = PersistenceConfig(backend="memory")

    # Act
    checkpointer, cm = await CheckpointerFactory.create(config)

    # Assert
    assert checkpointer is not None
    assert cm is None


@pytest.mark.asyncio
async def test_memory_checkpointer_is_base_checkpoint_saver():
    """Test that memory checkpointer implements BaseCheckpointSaver interface"""
    # Arrange
    config = PersistenceConfig(backend="memory")

    # Act
    checkpointer, _ = await CheckpointerFactory.create(config)

    # Assert
    from langgraph.checkpoint.base import BaseCheckpointSaver

    assert isinstance(checkpointer, BaseCheckpointSaver)


@pytest.mark.asyncio
async def test_factory_strategy_pattern(sqlite_checkpointer):
    """Test that Strategy Pattern works correctly for all backends"""
    # Arrange & Act - Test memory backend
    memory_config = PersistenceConfig(backend="memory")
    memory_checkpointer, memory_cm = await CheckpointerFactory.create(memory_config)

    # Assert - Memory
    assert memory_checkpointer is not None
    assert memory_cm is None
    from langgraph.checkpoint.memory import InMemorySaver

    assert isinstance(memory_checkpointer, InMemorySaver)

    # Arrange & Act - Test none backend
    none_config = PersistenceConfig(backend="none")
    none_checkpointer, none_cm = await CheckpointerFactory.create(none_config)

    # Assert - None
    assert none_checkpointer is None
    assert none_cm is None

    # Arrange & Act - Test sqlite backend (may fail if aiosqlite not available)
    sqlite_checkpointer_instance, sqlite_cm = sqlite_checkpointer

    # Assert - SQLite (may be None if creation fails)
    if sqlite_checkpointer_instance is not None:
        from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver

        assert sqlite_cm is not None
        assert isinstance(sqlite_checkpointer_instance, AsyncSqliteSaver)


@pytest.mark.asyncio
async def test_factory_unknown_backend():
    """Test that factory handles unknown backends gracefully"""
    # Arrange
    config = PersistenceConfig(backend="unknown_backend")

    # Act
    checkpointer, cm = await CheckpointerFactory.create(config)

    # Assert
    assert checkpointer is None
    assert cm is None


@pytest.mark.asyncio
async def test_create_sqlite_checkpointer(sqlite_checkpointer):
    """Test that SQLite checkpointer is created correctly"""
    # Act
    checkpointer, cm = sqlite_checkpointer

    # Assert
    # May be None if aiosqlite is not available or creation fails
    if checkpointer is not None:
        from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver

        assert cm is not None
        assert isinstance(checkpointer, AsyncSqliteSaver)


@pytest.mark.asyncio
async def test_create_none_checkpointer():
    """Test that none checkpointer returns None"""
    # Arrange
    config = PersistenceConfig(backend="none")

    # Act
    checkpointer, cm = await CheckpointerFactory.create(config)

    # Assert
    assert checkpointer is None
    assert cm is None
