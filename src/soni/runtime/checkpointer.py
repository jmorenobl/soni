"""Checkpointer factory.

Supports multiple backends:
- memory: In-memory (development/testing)
- sqlite: SQLite file-based (local persistence)
- postgres: PostgreSQL (production)
"""

import logging
from pathlib import Path
from typing import cast

from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.checkpoint.memory import MemorySaver

from soni.core.errors import ConfigError

logger = logging.getLogger(__name__)


def create_checkpointer(
    type: str = "memory",
    **kwargs,
) -> BaseCheckpointSaver:
    """Create a checkpointer instance.

    Args:
        type: Checkpointer type ("memory", "sqlite", or "postgres").
        kwargs: Backend-specific arguments:
            - sqlite: db_path (str or Path) - path to SQLite file
            - postgres: connection_string (str) - PostgreSQL connection URL

    Returns:
        BaseCheckpointSaver instance.

    Raises:
        ConfigError: If type is unknown or dependencies missing.
    """
    if type == "memory":
        logger.debug("Creating in-memory checkpointer")
        return MemorySaver()

    if type == "sqlite":
        return _create_sqlite_checkpointer(**kwargs)

    if type == "postgres":
        return _create_postgres_checkpointer(**kwargs)

    raise ConfigError(f"Unknown checkpointer type: {type}")


def _create_sqlite_checkpointer(**kwargs) -> BaseCheckpointSaver:
    """Create SQLite checkpointer.

    Note: Uses sync SqliteSaver since async version returns context manager.
    """
    try:
        from langgraph.checkpoint.sqlite import SqliteSaver
    except ImportError as e:
        raise ConfigError(
            "SQLite checkpointer requires 'langgraph-checkpoint-sqlite'. "
            "Install with: pip install langgraph-checkpoint-sqlite"
        ) from e

    db_path = kwargs.get("db_path", "checkpoints.db")
    path = Path(db_path)

    # Ensure parent directory exists
    path.parent.mkdir(parents=True, exist_ok=True)

    logger.info(f"Creating SQLite checkpointer at {path}")
    return cast(BaseCheckpointSaver, SqliteSaver.from_conn_string(str(path)))


def _create_postgres_checkpointer(**kwargs) -> BaseCheckpointSaver:
    """Create PostgreSQL checkpointer.

    Note: Uses sync PostgresSaver since async version returns context manager.
    """
    try:
        from langgraph.checkpoint.postgres import PostgresSaver
    except ImportError as e:
        raise ConfigError(
            "Postgres checkpointer requires 'langgraph-checkpoint-postgres'. "
            "Install with: pip install langgraph-checkpoint-postgres"
        ) from e

    connection_string = kwargs.get("connection_string")
    if not connection_string:
        raise ConfigError("Postgres checkpointer requires 'connection_string' kwarg")

    logger.info("Creating Postgres checkpointer")
    return cast(BaseCheckpointSaver, PostgresSaver.from_conn_string(connection_string))
