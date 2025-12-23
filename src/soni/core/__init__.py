"""Core domain types and infrastructure."""

from soni.core.message_sink import BufferedMessageSink, MessageSink, WebSocketMessageSink
from soni.core.pending_task import (
    CollectTask,
    ConfirmTask,
    InformTask,
    PendingTask,
    collect,
    confirm,
    inform,
    is_collect,
    is_confirm,
    is_inform,
    requires_input,
)
from soni.core.types import DialogueState

__all__ = [
    "DialogueState",
    "PendingTask",
    "CollectTask",
    "ConfirmTask",
    "InformTask",
    "collect",
    "confirm",
    "inform",
    "is_collect",
    "is_confirm",
    "is_inform",
    "requires_input",
    "MessageSink",
    "BufferedMessageSink",
    "WebSocketMessageSink",
]
