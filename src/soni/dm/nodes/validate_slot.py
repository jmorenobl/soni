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

    if not nlu_result:
        logger.warning("No NLU result in state for validate_slot_node")
        return {"conversation_state": "error"}

    # Get first slot from NLU result
    slots = nlu_result.get("slots", [])
    if not slots:
        # No slots extracted - this can happen if:
        # 1. NLU couldn't extract slots (e.g., no expected_slots in context)
        # 2. User message doesn't contain slot values
        # 3. Flow not started yet
        message_type = nlu_result.get("message_type", "")
        logger.warning(
            f"No slots in NLU result for message_type={message_type}. "
            f"This may indicate the flow needs to be started first or NLU needs better context."
        )

        # If this is a correction/modification but no slots, try to continue flow
        # The flow might need to be restarted or we need to collect slots differently
        flow_manager = runtime.context["flow_manager"]
        active_ctx = flow_manager.get_active_context(state)

        if active_ctx:
            # Flow is active but no slots extracted - continue to collect next slot
            return {"conversation_state": "waiting_for_slot"}
        else:
            # No flow active - this is an error state
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

        # Step 1: Capture current step and conversation_state BEFORE updating slot
        # This is critical for corrections/modifications to return to the correct step
        previous_step = active_ctx.get("current_step")
        previous_conversation_state = state.get("conversation_state")

        # Step 2: Detect if this is a correction or modification
        # Check both message_type and slot actions
        message_type = nlu_result.get("message_type", "")
        # Also check slot actions - a slot with CORRECT or MODIFY action indicates correction/modification
        slot_actions = [
            slot.get("action") if isinstance(slot, dict) else getattr(slot, "action", None)
            for slot in slots
        ]
        has_correct_or_modify_action = any(
            action in ("correct", "modify", "CORRECT", "MODIFY")
            for action in slot_actions
            if action
        )

        is_correction_or_modification = (
            message_type in ("correction", "modification") or has_correct_or_modify_action
        )

        logger.debug(
            f"validate_slot: message_type={message_type}, slot_actions={slot_actions}, "
            f"previous_step={previous_step}, is_correction_or_modification={is_correction_or_modification}"
        )

        flow_id = active_ctx["flow_id"]
        flow_slots = state.get("flow_slots", {}).copy()
        if flow_id not in flow_slots:
            flow_slots[flow_id] = {}
        flow_slots[flow_id][slot_name] = normalized_value

        # Update state with new slot value before checking if step is complete
        # This ensures is_step_complete sees the updated value
        state["flow_slots"] = flow_slots

        # Step 3: If correction/modification, return to previous step instead of advancing
        if is_correction_or_modification:
            # Determine which step to return to
            target_step = previous_step

            # Check if all required slots are filled - if so, we should be at a later step
            # This handles the case where all slots were provided at once but current_step
            # hasn't advanced correctly
            flow_config = step_manager.config.flows.get(active_ctx["flow_name"])
            all_slots_filled = False
            if flow_config:
                # Get all required slots from flow steps
                required_slots = set()
                for step in flow_config.steps:
                    if step.type == "collect" and step.slot:
                        required_slots.add(step.slot)

                # Check if all required slots are now filled (including the one we just updated)
                filled_slots = set(flow_slots[flow_id].keys())
                all_slots_filled = required_slots.issubset(filled_slots)

                logger.debug(
                    f"Correction check: required_slots={required_slots}, "
                    f"filled_slots={filled_slots}, all_slots_filled={all_slots_filled}"
                )

            # If all slots are filled, we should return to the last step (confirmation or action)
            # not to the first collect step
            if all_slots_filled and flow_config and flow_config.steps:
                # Find the last step in the flow (confirmation or action)
                for step in reversed(flow_config.steps):
                    if step.type in ("confirm", "action"):
                        target_step = step.step
                        logger.debug(
                            f"All slots filled, returning to last step '{target_step}' "
                            f"instead of '{previous_step}'"
                        )
                        break

            # If we were at confirmation/action state but target_step is still a collect step,
            # try to find the appropriate step from conversation_state
            if (
                target_step
                and previous_conversation_state
                in ("ready_for_action", "ready_for_confirmation", "executing_action", "confirming")
                and flow_config
                and flow_config.steps
            ):
                # Find step that matches the conversation_state
                for step in reversed(flow_config.steps):
                    if previous_conversation_state in ("ready_for_confirmation", "confirming"):
                        if step.type == "confirm":
                            target_step = step.step
                            break
                    elif previous_conversation_state in ("ready_for_action", "executing_action"):
                        if step.type == "action":
                            target_step = step.step
                            break

            # Fallback: if no target_step found, use the step that collects this slot
            if not target_step and flow_config and flow_config.steps:
                for step in flow_config.steps:
                    if step.type == "collect" and step.slot == slot_name:
                        target_step = step.step
                        break

            if target_step:
                # Get the target step configuration to determine conversation_state
                temp_state = {**state, "current_step": target_step}
                target_step_config = step_manager.get_current_step_config(
                    temp_state, runtime.context
                )

                if target_step_config:
                    # Map step type to conversation state
                    step_type_to_state = {
                        "action": "ready_for_action",
                        "collect": "waiting_for_slot",
                        "confirm": "ready_for_confirmation",
                        "branch": "understanding",
                        "say": "generating_response",
                    }
                    new_conversation_state = step_type_to_state.get(
                        target_step_config.type, previous_conversation_state
                    )

                    # Step 4: Handle special case for confirmation step
                    if target_step_config.type == "confirm":
                        # Ensure we return to confirmation state
                        new_conversation_state = "ready_for_confirmation"

                    # Restore target step in both DialogueState and FlowContext
                    flow_stack = state.get("flow_stack", []).copy()
                    if flow_stack:
                        # Update current_step in the active flow context
                        flow_stack[-1] = {**flow_stack[-1], "current_step": target_step}

                    logger.info(
                        f"Correction/modification detected: returning to step '{target_step}' "
                        f"(previous was '{previous_step}') with state '{new_conversation_state}'"
                    )

                    return {
                        "flow_slots": flow_slots,
                        "conversation_state": new_conversation_state,
                        "current_step": target_step,  # Update DialogueState.current_step
                        "flow_stack": flow_stack,  # Update FlowContext.current_step
                    }

        # Normal flow: Check if current step is complete
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
