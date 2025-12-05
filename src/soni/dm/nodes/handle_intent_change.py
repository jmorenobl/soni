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
    # push_flow modifies state["flow_stack"] and state["flow_slots"] in place
    # and initializes current_step to the first step of the flow
    flow_manager.push_flow(
        state,
        flow_name=command,
        inputs={},
        reason="intent_change",
    )

    # Get the current_step that push_flow set
    active_ctx = flow_manager.get_active_context(state)
    current_step = active_ctx["current_step"] if active_ctx else None

    # Get the first slot to collect from the current step
    step_manager = runtime.context["step_manager"]
    waiting_for_slot = None
    current_step_config = step_manager.get_current_step_config(state, runtime.context)
    if current_step_config and current_step_config.type == "collect":
        waiting_for_slot = current_step_config.slot

    # Return the modified state parts
    # IMPORTANT: Include flow_stack and flow_slots to propagate push_flow changes
    return {
        "conversation_state": "waiting_for_slot",
        "current_step": current_step,
        "waiting_for_slot": waiting_for_slot,
        "current_prompted_slot": waiting_for_slot,
        "flow_stack": state["flow_stack"],
        "flow_slots": state["flow_slots"],
    }
