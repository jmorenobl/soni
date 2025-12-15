"""Correction pattern handler."""

import logging
from typing import Any

from soni.core.commands import Command, CorrectSlot
from soni.core.constants import ConversationState
from soni.core.patterns.base import ConversationPattern
from soni.core.types import DialogueState, RuntimeContext

logger = logging.getLogger(__name__)


class CorrectionPattern(ConversationPattern):
    """Handles user corrections (e.g., "No, I meant Barcelona")."""

    @property
    def name(self) -> str:
        return "correction"

    def matches(self, command: Command, state: DialogueState) -> bool:
        return isinstance(command, CorrectSlot)

    async def handle(
        self, command: Command, state: DialogueState, context: RuntimeContext
    ) -> dict[str, Any]:
        if not isinstance(command, CorrectSlot):
            return {}

        slot_name = command.slot_name
        new_value = command.new_value

        logger.info(f"Handling correction: {slot_name} -> {new_value}")

        flow_manager = context.get("flow_manager")
        if flow_manager:
            if new_value:
                # Update slot with new value
                flow_manager.set_slot(state, slot_name=slot_name, value=new_value)
                updates = {
                    "conversation_state": ConversationState.GENERATING_RESPONSE,
                    "last_response": f"Updated {slot_name} to {new_value}.",
                    "flow_slots": state.get("flow_slots"),  # Return updated slots
                }
            else:
                # No value provided (e.g. "change destination") - Clear slot to force re-collection
                flow_manager.set_slot(state, slot_name=slot_name, value=None)
                updates = {
                    "conversation_state": ConversationState.GENERATING_RESPONSE,
                    "last_response": f"Okay, checking {slot_name}. What should it be?",
                    "flow_slots": state.get("flow_slots"),  # Return updated slots
                }
        else:
            updates = {}

        return updates
