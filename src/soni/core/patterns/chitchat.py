from typing import Any

from soni.core.commands import ChitChat, Command
from soni.core.patterns.base import ConversationPattern
from soni.core.types import DialogueState, RuntimeContext


class ChitChatPattern(ConversationPattern):
    """Handles CHIT_CHAT / DIGRESSION pattern."""

    @property
    def name(self) -> str:
        return "chitchat"

    def matches(self, command: Command, state: DialogueState) -> bool:
        return isinstance(command, ChitChat)

    async def handle(
        self, command: Command, state: DialogueState, context: RuntimeContext
    ) -> dict[str, Any]:
        if not isinstance(command, ChitChat):
            return {}

        # Simply update the last response with the hint if present
        # In a real system, this might call an LLM or predefined responses
        response = command.response_hint or "I see."

        return {
            "last_response": response,
            # We don't change state, or maybe we stay in current state?
            # If we return nothing for conversation_state, it stays as is.
        }
