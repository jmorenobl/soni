"""MessageSink interface for real-time message delivery.

This module defines the abstract interface and implementations for
streaming messages to users during flow execution.
"""

from abc import ABC, abstractmethod
from typing import Any


class MessageSink(ABC):
    """Interface for streaming messages to the user in real-time (DIP)."""

    @abstractmethod
    async def send(self, message: str) -> None:
        """Send a message to the user immediately."""
        ...


class BufferedMessageSink(MessageSink):
    """Buffers messages for testing or batch delivery."""

    def __init__(self) -> None:
        self.messages: list[str] = []

    async def send(self, message: str) -> None:
        """Append message to buffer."""
        self.messages.append(message)

    def clear(self) -> None:
        """Clear the message buffer."""
        self.messages.clear()


class WebSocketMessageSink(MessageSink):
    """WebSocket-based real-time delivery."""

    def __init__(self, websocket: Any) -> None:
        self._ws = websocket

    async def send(self, message: str) -> None:
        """Send message via WebSocket."""
        await self._ws.send_json({"type": "message", "content": message})
