"""Generate response node for final response generation."""

import logging
from typing import Any

from soni.core.types import DialogueState

logger = logging.getLogger(__name__)


async def generate_response_node(
    state: DialogueState,
    runtime: Any,  # Runtime[RuntimeContext] - using Any to avoid import issues
) -> dict:
    """
    Generate final response to user.

    Args:
        state: Current dialogue state
        runtime: Runtime context

    Returns:
        Partial state updates
    """
    # For now, simple response generation
    # TODO: Integrate with LLM for natural response generation

    action_result = state.get("action_result")
    if action_result:
        response = f"Action completed successfully. Result: {action_result}"
    else:
        response = "How can I help you?"

    return {
        "last_response": response,
        "conversation_state": "idle",
    }
