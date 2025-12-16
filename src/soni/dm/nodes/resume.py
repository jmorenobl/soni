"""Resume node for handling flow completion and stack resumption."""

import logging
from typing import Any

from langchain_core.runnables import RunnableConfig

from soni.core.errors import FlowStackError
from soni.core.types import DialogueState

logger = logging.getLogger(__name__)


async def resume_node(
    state: DialogueState,
    config: RunnableConfig,
) -> dict[str, Any]:
    """Handle flow completion and stack resumption.

    This node is called when a flow subgraph finishes execution.
    It manages the flow stack lifecycle:
    1. Pops the completed flow from the stack
    2. Determines if there are remaining flows to resume
    """
    context = config["configurable"]["runtime_context"]
    flow_manager = context.flow_manager

    # Check if we are just paused for input
    # If so, do NOT pop. Just pass through to respond.
    if state.get("flow_state") == "waiting_input":
        logger.debug("Flow waiting for input - skipping pop")
        return {"flow_stack": state.get("flow_stack")}

    # 1. Pop the completed flow
    try:
        completed_flow = await flow_manager.pop_flow(state, result="completed")
        logger.debug(f"Popped completed flow: {completed_flow['flow_name']}")
    except FlowStackError:
        logger.warning("Attempted to pop flow from empty stack in resume_node")
        return {"flow_stack": state.get("flow_stack", [])}

    # 2. Check remaining stack for resume intent
    active_ctx = flow_manager.get_active_context(state)
    if active_ctx:
        logger.info(f"Resuming parent flow: {active_ctx['flow_name']}")
    else:
        logger.debug("Stack empty after pop - ending turn")

    return {
        "flow_stack": state["flow_stack"],
    }
