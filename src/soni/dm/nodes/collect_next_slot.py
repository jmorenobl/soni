"""Collect next slot node with interrupt pattern."""

import logging
from typing import Any

from soni.core.state import get_all_slots
from soni.core.types import DialogueState, NodeRuntime

logger = logging.getLogger(__name__)


async def collect_next_slot_node(
    state: DialogueState,
    runtime: NodeRuntime,
) -> dict[str, Any]:
    """
    Ask for next required slot and pause execution.

    Uses interrupt() to wait for user response.

    Args:
        state: Current dialogue state
        runtime: Runtime context

    Returns:
        Partial state updates
    """
    # Import interrupt at runtime (not at module level)
    from langgraph.types import interrupt

    logger.info("Entering collect_next_slot_node")

    # Get active flow (idempotent operation - safe before interrupt)
    flow_manager = runtime.context["flow_manager"]
    step_manager = runtime.context["step_manager"]
    active_ctx = flow_manager.get_active_context(state)

    if not active_ctx:
        # No active flow - this shouldn't happen if routing is correct
        # But if it does, generate a response instead of going idle
        logger.warning("collect_next_slot called but no active flow context")
        return {
            "conversation_state": "idle",
            "last_response": "I'm not sure what you're asking for. Could you rephrase?",
        }

    # Get current step configuration
    current_step_config = step_manager.get_current_step_config(state, runtime.context)

    if not current_step_config:
        # No current step, try to get next step
        next_step_config = step_manager.get_next_step_config(state, runtime.context)
        if next_step_config and next_step_config.type == "collect":
            # Advance to next step
            _ = step_manager.advance_to_next_step(state, runtime.context)
            current_step_config = next_step_config
        else:
            return {"conversation_state": "error"}

    # Get next required slot from current step
    logger.info(f"Checking next required slot for flow {active_ctx['flow_id']}")
    slots = get_all_slots(state)
    logger.info(f"Current slots for flow: {slots}")

    next_slot = step_manager.get_next_required_slot(state, current_step_config, runtime.context)
    logger.info(f"Next required slot: {next_slot}")

    if not next_slot:
        logger.info("collect_next_slot: Slot filled, advancing...")
        # Check if we should advance to next step
        # Only advance if current step is 'collect' (implied completion since no slot needed)
        # For 'action', 'confirm', etc., we should NOT advance here as they need execution
        if current_step_config.type == "collect":
            step_updates = step_manager.advance_to_next_step(state, runtime.context)
            if step_updates:
                # CRITICAL: If we advanced to another 'waiting_for_slot' state (collect step),
                # we must override it to something else (e.g. 'understanding') to force
                # the Router to loop back to collect_next_slot.
                # Otherwise, Router sees 'waiting_for_slot' and ends the turn without prompting!
                if step_updates.get("conversation_state") == "waiting_for_slot":
                    step_updates["conversation_state"] = "understanding"
                return dict(step_updates)
            return {}
        else:
            # Not a collect step (e.g., action, confirm)
            # We must explicitly set the state so route_next can send to the correct node
            # otherwise we loop endlessly in COLLECT_NEXT_SLOT
            step_type = current_step_config.type
            updates = {}
            if step_type == "action":
                updates["conversation_state"] = "ready_for_action"
            elif step_type == "confirm":
                updates["conversation_state"] = "ready_for_confirmation"

            logger.info(
                f"collect_next_slot: delegating step '{current_step_config.step}' "
                f"type '{step_type}' to router with updates: {updates}"
            )
            return updates

    # Get slot configuration for proper prompt
    from soni.core.state import get_slot_config

    try:
        slot_config = get_slot_config(runtime.context, next_slot)
        prompt = (
            slot_config.prompt
            if hasattr(slot_config, "prompt")
            else f"Please provide your {next_slot}."
        )
    except KeyError:
        # Slot config not found, use generic prompt
        prompt = f"Please provide your {next_slot}."

    # CRITICAL: Set last_response BEFORE interrupt() so that if the flow goes to
    # generate_response (e.g., after a digression or after validate_slot), it has the correct prompt
    # The prompt will be shown to the user immediately
    result = {
        "last_response": prompt,
        "waiting_for_slot": next_slot,
        "current_prompted_slot": next_slot,
        "conversation_state": "waiting_for_slot",
        "action_result": None,  # Critical: Clear stale action results (e.g., from previous turns)
    }

    # Check if we're being called after validate_slot
    # After validate_slot, user_message is cleared, but we can detect this by checking
    # if the waiting_for_slot has changed (new slot) or if we're in a transition state
    # The key indicator: if current_prompted_slot in state differs from next_slot,
    # we're transitioning to a new slot after validation
    current_prompted_slot = state.get("current_prompted_slot")
    user_message = state.get("user_message", "")

    # If we have a user_message, this is a re-execution after interrupt (user responded)
    # In this case, we should NOT interrupt again - just return with the user_message
    if user_message and user_message.strip():
        result["user_message"] = user_message
        return result

    # If current_prompted_slot exists and is different from next_slot, we're transitioning
    # after validate_slot (user_message was cleared). Don't interrupt, just set last_response
    if current_prompted_slot and current_prompted_slot != next_slot:
        logger.info("=" * 80)
        logger.info("collect_next_slot: TRANSITIONING TO NEW SLOT (NO INTERRUPT)")
        logger.info(
            f"  Transitioning from '{current_prompted_slot}' to '{next_slot}' after validate_slot"
        )
        logger.info(f"  Setting last_response: '{prompt}'")
        logger.info(f"  Setting waiting_for_slot: '{next_slot}'")
        logger.info(f"  Setting current_prompted_slot: '{next_slot}'")
        logger.info("  Returning WITHOUT interrupt() - writes should apply before next node")
        logger.info(f"  RESULT TO RETURN: {result}")
        logger.info("=" * 80)
        return result

    # Initial call or no previous prompt - need to interrupt and wait for user response
    # Pause here - wait for user response
    # The prompt is passed as the interrupt value
    # It will be available in result['__interrupt__'] after ainvoke()
    user_response = interrupt(prompt)

    # Code after interrupt() executes when user responds
    # The node re-executes from the beginning, and interrupt() returns the resume value
    # Update result with user_message from resume
    result["user_message"] = user_response
    return result
