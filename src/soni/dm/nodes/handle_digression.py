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

    return {
        "last_response": response,
        "conversation_state": "generating_response",
        "digression_depth": state.get("digression_depth", 0) + 1,
        "last_digression_type": command,
    }
