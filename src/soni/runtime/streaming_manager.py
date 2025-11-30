"""Streaming management for dialogue responses"""

import logging
from collections.abc import AsyncGenerator
from typing import Any

from soni.core.state import DialogueState

logger = logging.getLogger(__name__)


class StreamingManager:
    """Manages streaming responses."""

    async def stream_response(
        self,
        graph: Any,
        state: DialogueState,
        user_id: str,
    ) -> AsyncGenerator[dict[str, Any], None]:
        """
        Stream dialogue processing events.

        Args:
            graph: Compiled LangGraph StateGraph
            state: Initial dialogue state
            user_id: Unique identifier for the user/conversation

        Yields:
            Events from graph execution
        """
        config = {"configurable": {"thread_id": user_id}}

        async for event in graph.astream(
            state.to_dict(),
            config=config,
            stream_mode="updates",
        ):
            yield event
