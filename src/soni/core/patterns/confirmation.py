"""Confirmation pattern handler."""

import logging
from typing import Any

from soni.core.commands import AffirmConfirmation, Command, DenyConfirmation
from soni.core.constants import ConversationState
from soni.core.patterns.base import ConversationPattern
from soni.core.types import DialogueState, RuntimeContext

logger = logging.getLogger(__name__)


class ConfirmationPattern(ConversationPattern):
    """Handles confirmation responses (Affirm/Deny)."""

    @property
    def name(self) -> str:
        return "confirmation"

    def matches(self, command: Command, state: DialogueState) -> bool:
        return isinstance(command, (AffirmConfirmation, DenyConfirmation))

    async def handle(
        self, command: Command, state: DialogueState, context: RuntimeContext
    ) -> dict[str, Any]:
        if isinstance(command, AffirmConfirmation):
            logger.info("Handling AffirmConfirmation")
            return {"conversation_state": ConversationState.READY_FOR_ACTION}

        if isinstance(command, DenyConfirmation):
            logger.info(f"Handling DenyConfirmation. Slot to change: {command.slot_to_change}")
            updates: dict[str, Any] = {"conversation_state": ConversationState.WAITING_FOR_SLOT}
            # If a slot to change is specified, we might want to hint the validator or collector
            # to focus on that slot.
            return updates

        return {}
