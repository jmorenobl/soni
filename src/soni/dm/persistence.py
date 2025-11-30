"""Persistence and checkpointing for dialogue state"""

import logging
from typing import Any

from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver

from soni.core.config import PersistenceConfig

logger = logging.getLogger(__name__)


class CheckpointerFactory:
    """Factory for creating checkpointers based on configuration."""

    @staticmethod
    async def create(persistence_config: PersistenceConfig) -> tuple[Any, Any]:
        """
        Create checkpointer from config.

        Args:
            persistence_config: Persistence configuration from settings

        Returns:
            Tuple of (checkpointer, context_manager)
            If backend is "none" or creation fails, returns (None, None)

        Raises:
            ValueError: If backend is unsupported
        """
        backend = persistence_config.backend

        if backend == "sqlite":
            try:
                # from_conn_string returns an async context manager
                # AsyncSqliteSaver requires aiosqlite and supports async methods
                checkpointer_cm = AsyncSqliteSaver.from_conn_string(persistence_config.path)
                # Enter the async context manager and return the checkpointer
                checkpointer = await checkpointer_cm.__aenter__()
                return checkpointer, checkpointer_cm
            except Exception as e:
                logger.warning(
                    f"Failed to create SQLite checkpointer: {e}. Using in-memory state only."
                )
                return None, None
        elif backend == "none":
            return None, None
        else:
            logger.warning(
                f"Unsupported persistence backend: {backend}. Using in-memory state only."
            )
            return None, None
