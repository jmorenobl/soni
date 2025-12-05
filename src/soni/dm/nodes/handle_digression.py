"""Handle digression node for questions without flow changes."""

import logging
from typing import Any

from soni.core.types import DialogueState

logger = logging.getLogger(__name__)


async def handle_digression_node(
    state: DialogueState,
    runtime: Any,  # Runtime[RuntimeContext] - using Any to avoid import issues
) -> dict:
    """
    Handle digression (question without flow change).

    Args:
        state: Current dialogue state
        runtime: Runtime context

    Returns:
        Partial state updates
    """
    nlu_result = state.get("nlu_result") or {}
    command = nlu_result.get("command", "") if nlu_result else ""

    # For now, generate simple response
    # TODO: Integrate with knowledge base or help system
    response = f"I understand you're asking about {command}. Let me help you with that."

    return {
        "last_response": response,
        "conversation_state": "generating_response",
        "digression_depth": state.get("digression_depth", 0) + 1,
        "last_digression_type": command,
    }
