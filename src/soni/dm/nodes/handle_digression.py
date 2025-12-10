"""Handle digression node for questions without flow changes."""

import logging

from soni.core.types import DialogueState, NodeRuntime
from soni.utils.response_generator import ResponseGenerator

logger = logging.getLogger(__name__)


async def handle_digression_node(
    state: DialogueState,
    runtime: NodeRuntime,
) -> dict:
    """
    Handle digression (question without flow change).

    Preserves the current slot collection state and re-prompts for the slot
    after answering the question.

    Args:
        state: Current dialogue state
        runtime: Runtime context

    Returns:
        Partial state updates
    """
    nlu_result = state.get("nlu_result") or {}
    command = nlu_result.get("command", "") if nlu_result else ""

    # Generate response using ResponseGenerator
    response = ResponseGenerator.generate_digression(command)

    # Preserve current slot collection state
    waiting_for_slot = state.get("waiting_for_slot")
    current_step = state.get("current_step")

    # If we're waiting for a slot, re-prompt after answering the question
    if waiting_for_slot:
        try:
            from soni.core.state import get_slot_config

            slot_config = get_slot_config(runtime.context, waiting_for_slot)
            prompt = (
                slot_config.prompt
                if hasattr(slot_config, "prompt") and slot_config.prompt
                else f"Please provide your {waiting_for_slot}."
            )
            # Combine digression response with slot re-prompt
            last_response = f"{response}\n\n{prompt}"
        except (KeyError, AttributeError):
            # If slot config not found, use generic prompt
            prompt = f"Please provide your {waiting_for_slot}."
            last_response = f"{response}\n\n{prompt}"

        logger.info(
            f"Digression handled: preserving waiting_for_slot='{waiting_for_slot}' "
            f"and re-prompting after question"
        )

        result = {
            "last_response": last_response,
            "conversation_state": "waiting_for_slot",
            "digression_depth": state.get("digression_depth", 0) + 1,
            "last_digression_type": command,
            "waiting_for_slot": waiting_for_slot,
        }

        # Preserve current_step if it exists
        if current_step:
            result["current_step"] = current_step

        return result

    # No slot waiting - just answer the question
    return {
        "last_response": response,
        "conversation_state": "generating_response",
        "digression_depth": state.get("digression_depth", 0) + 1,
        "last_digression_type": command,
    }
