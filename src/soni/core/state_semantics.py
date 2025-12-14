"""Semantics and validation for conversation states.

This module provides the "Single Source of Truth" for valid conversation states,
their meanings, and validation logic to ensure the system handles invalid
states gracefully.
"""

import logging

from soni.core.constants import ConversationState

logger = logging.getLogger(__name__)

# Semantic definitions for each state
# This table serves as both documentation and a validation source
STATE_SEMANTICS: dict[ConversationState, str] = {
    ConversationState.IDLE: "No flow active, waiting for user to initiate.",
    ConversationState.UNDERSTANDING: "Processing user message through NLU.",
    ConversationState.WAITING_FOR_SLOT: "Waiting for user to provide a slot value.",
    ConversationState.VALIDATING_SLOT: "Validating a slot value provided by the user.",
    ConversationState.READY_FOR_ACTION: "All slots filled, ready to execute action.",
    ConversationState.READY_FOR_CONFIRMATION: "All slots filled, ready to ask for confirmation.",
    ConversationState.CONFIRMING: "Asked for confirmation, waiting for user response.",
    ConversationState.EXECUTING_ACTION: "Executing the flow's action/side-effect.",
    ConversationState.GENERATING_RESPONSE: "Generating a response message for the user.",
    ConversationState.COMPLETED: "Flow has completed successfully.",
    ConversationState.ERROR: "An error occurred in the dialogue flow.",
    ConversationState.FALLBACK: "System is in an unknown or invalid state, requiring recovery.",
}


def validate_conversation_state(state: str | None) -> ConversationState:
    """Validate and normalize a conversation state string.

    Ensures that the state is a valid ConversationState enum member.
    If the state is invalid or None, it logs a warning and returns FALLBACK.

    Args:
        state: The raw state string from DialogueState.

    Returns:
        A valid ConversationState enum member.
    """
    if state is None:
        logger.warning("validate_conversation_state: State is None, defaulting to IDLE")
        return ConversationState.IDLE

    try:
        # StrEnum allows instantiation from string value
        return ConversationState(state)
    except ValueError:
        logger.error(
            f"validate_conversation_state: Invalid state '{state}' detected. "
            f"Falling back to {ConversationState.FALLBACK.value}.",
            extra={"invalid_state": state, "valid_states": list(ConversationState)},
        )
        return ConversationState.FALLBACK
