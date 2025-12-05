"""Handle intent change node for starting new flows."""

import logging
from typing import Any

from soni.core.types import DialogueState

logger = logging.getLogger(__name__)


async def handle_intent_change_node(
    state: DialogueState,
    runtime: Any,  # Runtime[RuntimeContext] - using Any to avoid import issues
) -> dict:
    """
    Start new flow based on intent change.

    Args:
        state: Current dialogue state
        runtime: Runtime context

    Returns:
        Partial state updates
    """
    flow_manager = runtime.context["flow_manager"]
    nlu_result = state.get("nlu_result", {})

    if not nlu_result:
        return {"conversation_state": "error"}

    command = nlu_result.get("command")
    if not command:
        return {"conversation_state": "error"}

    # Start new flow
    flow_manager.push_flow(
        state,
        flow_name=command,
        inputs={},
        reason="intent_change",
    )

    return {
        "conversation_state": "collecting",
        "current_step": None,
    }
