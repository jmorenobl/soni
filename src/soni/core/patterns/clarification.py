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
            # CRITICAL: End the turn here to show the explanation.
            # On next turn, the flow will resume and re-prompt (via collect_next_slot logic).
            "conversation_state": ConversationState.GENERATING_RESPONSE,
        }
