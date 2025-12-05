"""Execute action node for running actions."""

import logging
from typing import Any

from soni.core.types import DialogueState

logger = logging.getLogger(__name__)


async def execute_action_node(
    state: DialogueState,
    runtime: Any,  # Runtime[RuntimeContext] - using Any to avoid import issues
) -> dict:
    """
    Execute action via ActionHandler.

    Args:
        state: Current dialogue state
        runtime: Runtime context

    Returns:
        Partial state updates
    """
    action_handler = runtime.context["action_handler"]
    flow_manager = runtime.context["flow_manager"]

    active_ctx = flow_manager.get_active_context(state)
    if not active_ctx:
        return {"conversation_state": "error"}

    # Get action name from flow
    flow_name = active_ctx["flow_name"]

    # Get slots for action inputs
    flow_slots = state.get("flow_slots", {}).get(active_ctx["flow_id"], {})

    # Execute action
    try:
        action_result = await action_handler.execute(
            action_name=flow_name,
            inputs=flow_slots,
        )

        return {
            "conversation_state": "executing_action",
            "action_result": action_result,
        }
    except Exception as e:
        logger.error(f"Action execution failed: {e}")
        return {
            "conversation_state": "error",
            "action_error": str(e),
        }
