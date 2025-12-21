"""Extract and format streaming chunks from LangGraph."""

from dataclasses import dataclass
from typing import Any


@dataclass
class StreamChunk:
    """Normalized streaming chunk."""

    content: str
    node: str | None = None
    is_final: bool = False
    metadata: dict[str, Any] | None = None


class ResponseStreamExtractor:
    """Extract response content from LangGraph stream chunks.

    Handles different stream_mode formats and normalizes output.
    """

    def extract(self, chunk: Any, stream_mode: str) -> StreamChunk | None:
        """Extract content from a stream chunk.

        Args:
            chunk: Raw chunk from LangGraph astream()
            stream_mode: The stream mode used

        Returns:
            Normalized StreamChunk or None if chunk should be skipped
        """
        match stream_mode:
            case "updates":
                return self._extract_updates(chunk)
            case "values":
                return self._extract_values(chunk)
            case "custom":
                return self._extract_custom(chunk)
            case _:
                return StreamChunk(content=str(chunk))

    def _extract_updates(self, chunk: dict[str, Any]) -> StreamChunk | None:
        """Extract from updates stream mode (per-node updates).

        Updates mode yields {node_name: {state_updates}}
        We look for 'last_response' or other response fields.
        """
        for node, updates in chunk.items():
            # Skip internal nodes
            if node.startswith("__"):
                continue

            # Check for response content
            if isinstance(updates, dict):
                if "last_response" in updates:
                    return StreamChunk(
                        content=updates["last_response"],
                        node=node,
                        is_final=True,
                    )
                # Could also check for 'messages' with AIMessage
        return None

    def _extract_values(self, chunk: dict[str, Any]) -> StreamChunk | None:
        """Extract from values stream mode (full state)."""
        if "last_response" in chunk:
            return StreamChunk(
                content=chunk["last_response"],
                is_final=True,
            )
        return None

    def _extract_custom(self, chunk: Any) -> StreamChunk | None:
        """Extract from custom stream mode (user-defined data)."""
        if isinstance(chunk, str):
            return StreamChunk(content=chunk)
        elif isinstance(chunk, dict) and "content" in chunk:
            return StreamChunk(
                content=chunk["content"],
                metadata=chunk.get("metadata"),
            )
        return StreamChunk(content=str(chunk))
