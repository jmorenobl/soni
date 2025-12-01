"""Persistence and checkpointing for dialogue state"""

import logging
from typing import Any

from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver

from soni.core.config import PersistenceConfig

logger = logging.getLogger(__name__)


class CheckpointerFactory:
    """Factory for creating checkpointers based on configuration.

    Uses Strategy Pattern to support multiple persistence backends.
    Each backend has its own creation method, making the factory extensible
    without modifying existing code (Open/Closed Principle).
    """

    @staticmethod
    async def create(persistence_config: PersistenceConfig) -> tuple[Any, Any]:
        """
        Create checkpointer from config using Strategy Pattern.

        Args:
            persistence_config: Persistence configuration from settings

        Returns:
            Tuple of (checkpointer, context_manager)
            If backend is "none" or creation fails, returns (None, None)

        Raises:
            ValueError: If backend is unsupported
        """
        backend = persistence_config.backend

        # Strategy Pattern: route to appropriate creator method
        if backend == "sqlite":
            return await CheckpointerFactory._create_sqlite_checkpointer(persistence_config)
        elif backend == "memory":
            return await CheckpointerFactory._create_memory_checkpointer(persistence_config)
        elif backend == "none":
            return await CheckpointerFactory._create_none_checkpointer(persistence_config)
        else:
            # Fallback for unknown backends
            logger.warning(
                f"Unsupported persistence backend: {backend}. Using in-memory state only."
            )
            return None, None

    @staticmethod
    async def _create_sqlite_checkpointer(
        config: PersistenceConfig,
    ) -> tuple[Any, Any]:
        """
        Create SQLite checkpointer.

        Args:
            config: Persistence configuration

        Returns:
            Tuple of (checkpointer, context_manager)
        """
        try:
            # from_conn_string returns an async context manager
            # AsyncSqliteSaver requires aiosqlite and supports async methods
            checkpointer_cm = AsyncSqliteSaver.from_conn_string(config.path)
            # Enter the async context manager and return the checkpointer
            checkpointer = await checkpointer_cm.__aenter__()
            return checkpointer, checkpointer_cm
        except (OSError, ConnectionError, ImportError) as e:
            # Expected errors when creating checkpointer
            logger.warning(
                f"Failed to create SQLite checkpointer: {e}. Using in-memory state only.",
                extra={"error_type": type(e).__name__},
            )
            return None, None
        except Exception as e:
            # Unexpected errors
            logger.error(
                f"Unexpected error creating checkpointer: {e}",
                exc_info=True,
            )
            return None, None

    @staticmethod
    async def _create_memory_checkpointer(
        config: PersistenceConfig,
    ) -> tuple[Any, Any]:
        """
        Create in-memory checkpointer for testing.

        InMemorySaver does not require a context manager, so we return None
        for the context manager. This is ideal for tests as it provides
        complete isolation between test runs.

        Args:
            config: Persistence configuration (path is ignored for memory backend)

        Returns:
            Tuple of (checkpointer, None) - InMemorySaver does not need context manager
        """
        from langgraph.checkpoint.memory import InMemorySaver

        checkpointer = InMemorySaver()
        # InMemorySaver does not require context manager
        return checkpointer, None

    @staticmethod
    async def _create_none_checkpointer(
        config: PersistenceConfig,
    ) -> tuple[Any, Any]:
        """
        Create no-op checkpointer (no persistence).

        Args:
            config: Persistence configuration

        Returns:
            Tuple of (None, None) - no persistence
        """
        return None, None
