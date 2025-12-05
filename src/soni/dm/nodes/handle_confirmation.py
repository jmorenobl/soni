"""Handle confirmation response node for processing user confirmation (yes/no)."""

import logging
from typing import Any

from soni.core.types import DialogueState

logger = logging.getLogger(__name__)


async def handle_confirmation_node(
    state: DialogueState,
    runtime: Any,  # Runtime[RuntimeContext] - using Any to avoid import issues
) -> dict:
    """
    Handle user's confirmation response.

    This node processes the user's yes/no response to a confirmation request.
    The NLU should have already classified the response using ConfirmationSignature,
    so we just need to act on the structured result.

    Args:
        state: Current dialogue state
        runtime: Runtime context

    Returns:
        Partial state updates based on confirmation result
    """
    nlu_result = state.get("nlu_result") or {}
    message_type = nlu_result.get("message_type") if nlu_result else None

    # Sanity check: should be a confirmation response
    if message_type != "confirmation":
        # Edge case: user said something unrelated during confirmation
        # Treat as digression or ask again
        logger.warning(
            f"Expected confirmation but got message_type={message_type}, treating as digression"
        )
        return {"conversation_state": "understanding"}

    # Get confirmation value from NLU result
    # The NLU should extract this as True/False
    confirmation_value = nlu_result.get("confirmation_value") if nlu_result else None

    # User confirmed
    if confirmation_value is True:
        logger.info("User confirmed, proceeding to action")
        return {
            "conversation_state": "ready_for_action",
            "last_response": "Great! Processing your request...",
        }

    # User denied - wants to change something
    elif confirmation_value is False:
        logger.info("User denied confirmation, allowing modification")
        # For now, go back to understanding to allow user to modify
        # In the future, we could route to a specific modification handler
        return {
            "conversation_state": "understanding",
            "last_response": "What would you like to change?",
        }

    # Confirmation value not extracted or unclear
    else:
        logger.warning(f"Confirmation value unclear: {confirmation_value}, asking again")
        return {
            "conversation_state": "confirming",
            "last_response": "I didn't understand. Is this information correct? (yes/no)",
        }
