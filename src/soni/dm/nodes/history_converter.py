"""Converter for message history formats."""

import logging
from collections.abc import Sequence

from langchain_core.messages import BaseMessage, HumanMessage

logger = logging.getLogger(__name__)


class HistoryConverter:
    """Converts message history between formats.

    Handles conversion from LangGraph message format to formats
    expected by different NLU components.
    """

    @staticmethod
    def to_nlu_format(
        messages: Sequence[BaseMessage], max_history: int = 10
    ) -> list[dict[str, str]]:
        """Convert LangGraph messages to NLU input format.

        Args:
            messages: LangGraph message sequence
            max_history: Maximum number of messages to include

        Returns:
            List of dicts with 'role' and 'content' keys.
        """
        result: list[dict[str, str]] = []
        for msg in messages[-max_history:]:
            role = "user" if hasattr(msg, "type") and msg.type == "human" else "assistant"
            content = msg.content if hasattr(msg, "content") else str(msg)
            result.append({"role": role, "content": str(content)})
        return result

    @staticmethod
    def get_last_user_message(messages: Sequence[BaseMessage]) -> str:
        """Extract the last user message from history.

        Returns:
            The content of the last human message.

        Raises:
            ValueError: If no user message found.
        """
        for msg in reversed(messages):
            if isinstance(msg, HumanMessage) or (hasattr(msg, "type") and msg.type == "human"):
                return str(msg.content)
        return ""
