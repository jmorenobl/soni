"""Checkpointer factory."""

from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.checkpoint.memory import MemorySaver


def create_checkpointer(type: str = "memory", **kwargs) -> BaseCheckpointSaver:
    """Create a checkpointer instance.

    Args:
        type: Checkpointer type ("memory" or "sqlite" - sqlite not yet impl dependency).
        kwargs: Arguments for the checkpointer.

    Returns:
        BaseCheckpointSaver instance.
    """
    if type == "memory":
        return MemorySaver()

    # TODO: Add Sqlite/Postgres support
    raise ValueError(f"Unknown checkpointer type: {type}")
