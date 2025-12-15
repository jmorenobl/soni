"""Cancellation pattern handler."""

import logging
from typing import Any

from soni.core.commands import CancelFlow, Command
from soni.core.constants import ConversationState
from soni.core.patterns.base import ConversationPattern
from soni.core.types import DialogueState, RuntimeContext

logger = logging.getLogger(__name__)


class CancellationPattern(ConversationPattern):
    """Handles flow cancellation (e.g., "Cancel", "Never mind")."""

    @property
    def name(self) -> str:
        return "cancellation"

    def matches(self, command: Command, state: DialogueState) -> bool:
        return isinstance(command, CancelFlow)

    async def handle(
        self, command: Command, state: DialogueState, context: RuntimeContext
    ) -> dict[str, Any]:
        if not isinstance(command, CancelFlow):
            return {}

        logger.info(f"Handling cancellation: reason={command.reason}")

        # In real logic:
        # context.flow_manager.pop_flow()

        return {
            "conversation_state": ConversationState.IDLE,
            "flow_stack": [],  # Simplistic "clear stack"
            "last_response": "Cancelled. What else can I do for you?",
        }
