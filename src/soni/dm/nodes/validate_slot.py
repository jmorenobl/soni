"""Validate slot node for slot validation and normalization."""

import logging
from typing import Any

from soni.core.types import DialogueState

logger = logging.getLogger(__name__)


async def validate_slot_node(
    state: DialogueState,
    runtime: Any,  # Runtime[RuntimeContext] - using Any to avoid import issues
) -> dict:
    """
    Validate and normalize slot value.

    Args:
        state: Current dialogue state
        runtime: Runtime context with dependencies

    Returns:
        Partial state updates
    """
    normalizer = runtime.context["normalizer"]
    nlu_result = state.get("nlu_result", {})

    if not nlu_result or not nlu_result.get("slots"):
        return {"conversation_state": "error"}

    # Get first slot from NLU result
    slots = nlu_result.get("slots", [])
    if not slots:
        return {"conversation_state": "error"}

    slot = slots[0]

    # Handle different slot formats (dict or SlotValue model)
    if hasattr(slot, "name"):
        # SlotValue model
        slot_name = slot.name
        raw_value = slot.value
    elif isinstance(slot, dict):
        slot_name = slot.get("name")
        raw_value = slot.get("value")
    elif isinstance(slot, str):
        # Just a string value - use waiting_for_slot as the slot name
        slot_name = state.get("waiting_for_slot")
        raw_value = slot
    else:
        logger.error(f"Unknown slot format: {type(slot)}")
        return {"conversation_state": "error"}

    # Normalize slot value
    try:
        # Use normalize_slot which takes (slot_name, value) and handles config lookup
        normalized_value = await normalizer.normalize_slot(slot_name, raw_value)

        # Update flow slots
        flow_manager = runtime.context["flow_manager"]
        step_manager = runtime.context["step_manager"]
        active_ctx = flow_manager.get_active_context(state)

        if not active_ctx:
            return {"conversation_state": "error"}

        flow_id = active_ctx["flow_id"]
        flow_slots = state.get("flow_slots", {}).copy()
        if flow_id not in flow_slots:
            flow_slots[flow_id] = {}
        flow_slots[flow_id][slot_name] = normalized_value

        # Update state with new slot value before checking if step is complete
        # This ensures is_step_complete sees the updated value
        state["flow_slots"] = flow_slots

        # Check if current step is complete
        current_step_config = step_manager.get_current_step_config(state, runtime.context)
        if current_step_config:
            is_complete = step_manager.is_step_complete(state, current_step_config, runtime.context)

            if is_complete:
                # Step is complete, advance to next step
                updates: dict[str, Any] = dict(
                    step_manager.advance_to_next_step(state, runtime.context)
                )
                updates["flow_slots"] = flow_slots

                # Determine conversation_state based on next step type
                # Get the updated state to check the next step
                updated_state = {**state, **updates}
                next_step_config = step_manager.get_current_step_config(
                    updated_state, runtime.context
                )

                if next_step_config:
                    # Map step type to conversation state
                    step_type_to_state = {
                        "action": "ready_for_action",
                        "collect": "waiting_for_slot",
                        "confirm": "ready_for_confirmation",
                        "branch": "understanding",  # Branching logic will be handled by router
                        "say": "generating_response",
                    }
                    new_conversation_state = step_type_to_state.get(
                        next_step_config.type, "understanding"
                    )
                    updates["conversation_state"] = new_conversation_state
                else:
                    # No next step or flow completed
                    updates["conversation_state"] = "generating_response"

                return updates
            else:
                # Step not complete yet, stay in current step
                return {
                    "flow_slots": flow_slots,
                    "conversation_state": "waiting_for_slot",
                }
        else:
            # No current step config, just update slots
            return {
                "flow_slots": flow_slots,
                "conversation_state": "validating_slot",
            }
    except Exception as e:
        logger.error(f"Validation failed for slot {slot_name}: {e}")
        return {
            "conversation_state": "error",
            "validation_error": str(e),
        }
