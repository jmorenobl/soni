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
            # Advance step to move past 'confirm' step to the subsequent 'action' step
            step_manager = context["step_manager"]
            updates = step_manager.advance_to_next_step(state, context)
            return updates

        if isinstance(command, DenyConfirmation):
            logger.info(f"Handling DenyConfirmation. Slot to change: {command.slot_to_change}")

            if not command.slot_to_change:
                # If no specific slot indicated (e.g. just "No" or ambiguous "maybe"),
                # ask for clarification.
                return {
                    "conversation_state": ConversationState.GENERATING_RESPONSE,
                    "last_response": "I didn't understand what specific detail you'd like to change. Please tell me what to update.",
                }

            updates: dict[str, Any] = {
                "conversation_state": ConversationState.GENERATING_RESPONSE,
                "last_response": "Okay, I can update that. What would you like to change?",
            }
            # If a slot to change is specified, we might want to hint the validator or collector
            # to focus on that slot.
            return updates

        return {}
