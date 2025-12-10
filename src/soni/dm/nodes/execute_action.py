"""Execute action node for running actions."""

import logging
from typing import Any

from soni.core.types import DialogueState, NodeRuntime

logger = logging.getLogger(__name__)


async def execute_action_node(
    state: DialogueState,
    runtime: NodeRuntime,
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
    step_manager = runtime.context["step_manager"]

    active_ctx = flow_manager.get_active_context(state)
    if not active_ctx:
        return {"conversation_state": "error"}

    # Get current step configuration
    current_step_config = step_manager.get_current_step_config(state, runtime.context)

    if not current_step_config or current_step_config.type != "action":
        logger.error("Current step is not an action step")
        return {"conversation_state": "error"}

    # Get action name from step config
    action_name = current_step_config.call
    if not action_name:
        logger.error(f"Action step '{current_step_config.step}' has no 'call' field")
        return {"conversation_state": "error"}

    # Get slots for action inputs
    flow_slots = state.get("flow_slots", {}).get(active_ctx["flow_id"], {})

    # Execute action
    try:
        action_result = await action_handler.execute(
            action_name=action_name,
            inputs=flow_slots,
        )

        # Map outputs to slots if mapping specified
        updates: dict[str, Any] = {
            "action_result": action_result,
        }

        if current_step_config.map_outputs:
            from soni.core.state import get_all_slots, set_all_slots

            mapped_slots: dict[str, Any] = {}
            for state_var, action_output in current_step_config.map_outputs.items():
                if action_output in action_result:
                    mapped_slots[state_var] = action_result[action_output]
            if mapped_slots:
                current_slots = get_all_slots(state)
                current_slots.update(mapped_slots)
                set_all_slots(state, current_slots)
                updates["flow_slots"] = state.get("flow_slots", {})
        else:
            # No mapping - store all action results as slots
            if action_result:
                from soni.core.state import get_all_slots, set_all_slots

                current_slots = get_all_slots(state)
                current_slots.update(action_result)
                set_all_slots(state, current_slots)
                updates["flow_slots"] = state.get("flow_slots", {})

        # Advance to next step after action execution
        # This will set conversation_state based on next step type
        step_updates = step_manager.advance_to_next_step(state, runtime.context)
        updates.update(step_updates)

        # Log the final conversation_state for debugging
        logger.info(
            f"execute_action_node completed: action={action_name}, "
            f"conversation_state={updates.get('conversation_state')}"
        )

        return updates
    except Exception as e:
        logger.error(f"Action execution failed: {e}")
        return {
            "conversation_state": "error",
            "action_error": str(e),
        }
