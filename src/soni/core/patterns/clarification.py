"""Clarification pattern handler."""

import logging
from typing import Any

from soni.core.commands import Clarify, Command
from soni.core.patterns.base import ConversationPattern
from soni.core.types import DialogueState, RuntimeContext

logger = logging.getLogger(__name__)


class ClarificationPattern(ConversationPattern):
    """Handles user clarification requests (e.g., "Why do you need this?")."""

    @property
    def name(self) -> str:
        return "clarification"

    def matches(self, command: Command, state: DialogueState) -> bool:
        return isinstance(command, Clarify)

    async def handle(
        self, command: Command, state: DialogueState, context: RuntimeContext
    ) -> dict[str, Any]:
        if not isinstance(command, Clarify):
            return {}

        logger.info(f"Handling clarification request on topic: {command.topic}")

        # Usage of context to generate explanation would go here.
        explanation = f"I need this information because {command.topic or 'it is required'}."

        return {
            "last_response": explanation,
            # We usually stay in the same state or go to 'generating_response'
            # but we want to re-prompt.
            # In a graph, we might route to generate_response then back to collect_next_slot?
            # Or just update response and let the graph loop.
        }
