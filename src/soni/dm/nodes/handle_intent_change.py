"""Handle intent change node for starting new flows."""

import logging
from typing import Any

from soni.core.types import DialogueState

logger = logging.getLogger(__name__)


def _extract_slots_from_nlu(nlu_result: dict[str, Any]) -> dict[str, Any]:
    """Extract slots from NLU result.

    Args:
        nlu_result: NLU result dictionary containing slots

    Returns:
        Dictionary of extracted slots: {slot_name: slot_value}
    """
    slots_from_nlu = nlu_result.get("slots", [])
    extracted_slots: dict[str, Any] = {}

    for slot in slots_from_nlu:
        if isinstance(slot, dict):
            slot_name = slot.get("name")
            slot_value = slot.get("value")
            if slot_name and slot_value is not None:
                extracted_slots[slot_name] = slot_value
        elif hasattr(slot, "name") and hasattr(slot, "value"):
            # SlotValue model
            extracted_slots[slot.name] = slot.value

    return extracted_slots


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
        logger.warning("No command in NLU result for intent change")
        return {
            "conversation_state": "idle",
            "last_response": "I didn't understand what you want to do. Could you rephrase?",
        }

    # Normalize command to find matching flow
    # Use activate_flow_by_intent to handle variations (spaces, hyphens, etc.)
    from soni.core.state import get_current_flow
    from soni.dm.routing import activate_flow_by_intent

    config = runtime.context["config"]
    current_flow = get_current_flow(state)
    flow_name = activate_flow_by_intent(command, current_flow, config)

    # Check if we found a valid flow
    if flow_name == current_flow and command not in config.flows:
        # No flow was activated (normalization didn't find a match)
        # BUT: If we already have an active flow, this is likely a slot value, not an intent change
        # Don't break the flow - return idle to let validate_slot handle it
        active_ctx = flow_manager.get_active_context(state)
        if active_ctx:
            # We have an active flow - this might be a slot value, not an intent change
            # Return idle so routing goes to generate_response (validate_slot should have handled it)
            logger.info(
                f"Command '{command}' not a flow, but flow '{active_ctx['flow_name']}' is active. "
                f"This is likely a slot value - validate_slot should handle it. Returning idle."
            )
            return {
                "conversation_state": "idle",
                "last_response": "I didn't understand that. Could you rephrase?",
            }

        # No active flow and command not found - this is an error
        logger.warning(
            f"Flow '{command}' not found in config. Available flows: {list(config.flows.keys())}"
        )
        return {
            "conversation_state": "idle",
            "last_response": (
                f"I don't know how to {command}. "
                f"I can help you with: {', '.join(config.flows.keys())}"
            ),
        }

    # Check if flow is already active (may have been activated by understand_node)
    # If so, preserve existing slots and just update the state
    active_ctx = flow_manager.get_active_context(state)
    if active_ctx and active_ctx["flow_name"] == flow_name:
        # Flow already active - preserve existing slots and just update state
        existing_slots = state.get("flow_slots", {}).get(active_ctx["flow_id"], {})
        logger.info(
            f"Flow '{flow_name}' already active, preserving existing slots. Slots: {existing_slots}"
        )
        current_step = active_ctx.get("current_step")
        step_manager = runtime.context["step_manager"]
        waiting_for_slot = None
        current_step_config = step_manager.get_current_step_config(state, runtime.context)
        if current_step_config and current_step_config.type == "collect":
            waiting_for_slot = current_step_config.slot

        # CRITICAL: Preserve flow_slots to avoid losing slots that were saved by understand_node
        return {
            "conversation_state": "waiting_for_slot",
            "current_step": current_step,
            "waiting_for_slot": waiting_for_slot,
            "current_prompted_slot": waiting_for_slot,
            "flow_slots": state.get("flow_slots", {}),  # Preserve existing slots
        }

    # Start new flow with normalized flow name
    # push_flow modifies state["flow_stack"] and state["flow_slots"] in place
    # and initializes current_step to the first step of the flow
    flow_manager.push_flow(
        state,
        flow_name=flow_name,
        inputs={},
        reason="intent_change",
    )

    # Get the current_step that push_flow set
    active_ctx = flow_manager.get_active_context(state)
    current_step = active_ctx["current_step"] if active_ctx else None

    # CRITICAL: Save slots from nlu_result if they were extracted
    # This handles the case where user provides multiple slots in one message
    # (e.g., "I want to fly from New York to Los Angeles")
    if active_ctx:
        from soni.core.state import get_all_slots, set_all_slots

        # Extract slots from NLU result using helper
        extracted_slots = _extract_slots_from_nlu(nlu_result)

        if extracted_slots:
            # Get current slots and merge with extracted slots
            current_slots = get_all_slots(state)
            current_slots.update(extracted_slots)
            set_all_slots(state, current_slots)
            logger.info(
                f"Saved {len(extracted_slots)} slot(s) from NLU result: {list(extracted_slots.keys())}"
            )

    # After saving slots, advance through all completed steps
    step_manager = runtime.context["step_manager"]
    updates: dict[str, Any] = dict(
        step_manager.advance_through_completed_steps(state, runtime.context)
    )

    # IMPORTANT: Include flow_stack and flow_slots to propagate changes
    updates["flow_stack"] = state["flow_stack"]
    updates["flow_slots"] = state["flow_slots"]

    # CRITICAL: Clear user_message after processing to avoid re-processing
    # The message has been fully processed (slots saved, step advanced)
    # If we're advancing to a collect step, we'll wait for a new user message
    updates["user_message"] = ""  # Clear to prevent re-processing

    # If no updates from advance_through_completed_steps (shouldn't happen), set defaults
    if not updates.get("conversation_state"):
        # Get the first slot to collect
        current_step_config = step_manager.get_current_step_config(state, runtime.context)
        waiting_for_slot = None
        if current_step_config and current_step_config.type == "collect":
            waiting_for_slot = current_step_config.slot

        updates.update(
            {
                "conversation_state": "waiting_for_slot",
                "current_step": current_step,
                "waiting_for_slot": waiting_for_slot,
                "current_prompted_slot": waiting_for_slot,
            }
        )

    # Return the updates (already includes all necessary fields from advance_through_completed_steps)
    return updates
