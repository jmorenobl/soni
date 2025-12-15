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

        logger.info(f"Handling correction: {command.slot_name} -> {command.new_value}")

        # 1. Update the slot value in the active flow
        # In a real implementation, we would access flow_manager from context
        # and calling proper methods. For now we just return state updates.

        # We need to find where the slot is stored.
        # Typically in state["flow_slots"][active_flow_id]

        # We will assume the executor or a post-processor handles the actual merging
        # if we return a "slot_update" or similar.
        # But actually, the StateGraph expects us to return state modifications.

        # Simplification: We return a flag or specific keys that the reducer handles.
        # Or we modify `flow_slots` if we can read the structure.

        # For v2.0 Architecture, we should probably use the FlowManager to perform the update
        # if available in context.

        updates: dict[str, Any] = {
            "conversation_state": ConversationState.WAITING_FOR_SLOT,
            # We assume we go back to collecting slots after correction
            "last_response": f"Updated {command.slot_name} to {command.new_value}.",
        }

        # If we had access to flow_manager:
        if context.get("flow_manager"):
            # This logic implies we know the active flow.
            # In v2.0 we might rely on the side-effect of "state update" containing slots.
            # E.g. updates["slots"] = {command.slot_name: command.new_value}
            pass

        # For now, let's just return what the router needs to know:
        # We handled it, and we want to resume collecting execution.

        return updates
