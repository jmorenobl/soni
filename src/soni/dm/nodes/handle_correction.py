"""Handle correction node for slot corrections."""

import logging
from typing import Any

from soni.core.types import DialogueState, NodeRuntime
from soni.utils.metadata_manager import MetadataManager

logger = logging.getLogger(__name__)


async def handle_correction_node(
    state: DialogueState,
    runtime: NodeRuntime,
) -> dict:
    """
    Handle slot correction.

    When user corrects a previously provided slot value:
    1. Extract slot and new value from NLU result
    2. Update slot in state
    3. Set state variables (_correction_slot, _correction_value)
    4. Return to the step where user was (not advance)

    Args:
        state: Current dialogue state
        runtime: Runtime context with dependencies

    Returns:
        Partial state updates
    """
    nlu_result = state.get("nlu_result", {})

    if not nlu_result:
        logger.warning("No NLU result in state for handle_correction_node")
        return {"conversation_state": "error"}

    slots = nlu_result.get("slots", [])
    if not slots:
        logger.warning("No slots in NLU result for correction")
        # If no slots but flow is active, continue to collect
        flow_manager = runtime.context["flow_manager"]
        active_ctx = flow_manager.get_active_context(state)
        if active_ctx:
            return {"conversation_state": "waiting_for_slot"}
        return {"conversation_state": "error"}

    # Get first slot (corrections typically have one slot)
    slot = slots[0]

    # Extract slot name and value
    if hasattr(slot, "name"):
        slot_name = slot.name
        raw_value = slot.value
    elif isinstance(slot, dict):
        slot_name = slot.get("name")
        raw_value = slot.get("value")
    else:
        logger.error(f"Unknown slot format: {type(slot)}")
        return {"conversation_state": "error"}

    # Normalize value
    normalizer = runtime.context["normalizer"]
    try:
        normalized_value = await normalizer.normalize_slot(slot_name, raw_value)
    except Exception as e:
        logger.error(f"Normalization failed for correction: {e}")
        return {"conversation_state": "error"}

    # Update slot in state
    flow_manager = runtime.context["flow_manager"]
    step_manager = runtime.context["step_manager"]
    active_ctx = flow_manager.get_active_context(state)

    if not active_ctx:
        return {"conversation_state": "error"}

    # Capture current step and conversation_state BEFORE updating slot
    previous_step = active_ctx.get("current_step")
    previous_conversation_state = state.get("conversation_state")

    flow_id = active_ctx["flow_id"]
    flow_slots = state.get("flow_slots", {}).copy()
    if flow_id not in flow_slots:
        flow_slots[flow_id] = {}

    # Update slot
    flow_slots[flow_id][slot_name] = normalized_value

    # Set state variables (for Task 004)
    metadata = state.get("metadata", {})
    metadata = MetadataManager.set_correction_flags(metadata, slot_name, normalized_value)

    # Determine which step to return to (reuse logic from validate_slot)
    target_step = previous_step

    # Check if all required slots are filled - if so, we should be at a later step
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

    # Get acknowledgment message using template (Task 005)
    config = runtime.context["config"]
    logger.info(
        f"handle_correction: Generating acknowledgment for slot '{slot_name}' "
        f"with new value '{normalized_value}'"
    )
    acknowledgment = _get_response_template(
        config,
        "correction_acknowledged",
        "Got it, I've updated {slot_name} to {new_value}.",
        slot_name=slot_name,
        new_value=normalized_value,
    )
    logger.info(f"handle_correction: Generated acknowledgment: '{acknowledgment}'")

    if target_step:
        # Get the target step configuration to determine conversation_state
        temp_state = {**state, "current_step": target_step}
        target_step_config = step_manager.get_current_step_config(temp_state, runtime.context)

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

            # Handle special case for confirmation step
            if target_step_config.type == "confirm":
                new_conversation_state = "ready_for_confirmation"
                # For confirmation, combine acknowledgment with confirmation message
                # (confirmation will be re-displayed by confirm_action node)
                # CRITICAL: Use acknowledgment as last_response so it's shown before confirmation
                last_response = acknowledgment
                logger.info(
                    f"handle_correction: Returning to confirmation step, "
                    f"using acknowledgment as last_response: '{last_response}'"
                )
            elif target_step_config.type == "collect":
                # For collect steps, check if there's a next slot to prompt for
                # This handles the case where we corrected a slot but need to continue collecting
                next_slot = step_manager.get_next_required_slot(
                    {**state, "flow_slots": flow_slots, "current_step": target_step},
                    target_step_config,
                    runtime.context,
                )

                if next_slot:
                    # Get prompt for the next slot
                    try:
                        from soni.core.state import get_slot_config

                        slot_config = get_slot_config(runtime.context, next_slot)
                        next_prompt = (
                            slot_config.prompt
                            if hasattr(slot_config, "prompt") and slot_config.prompt
                            else f"Please provide your {next_slot}."
                        )
                        # Combine acknowledgment with next slot prompt
                        last_response = f"{acknowledgment}\n\n{next_prompt}"
                    except (KeyError, AttributeError):
                        # If slot config not found, use generic prompt
                        last_response = f"{acknowledgment}\n\nPlease provide your {next_slot}."
                else:
                    # No next slot to collect, just show acknowledgment
                    last_response = acknowledgment
            else:
                last_response = acknowledgment

            # Restore target step in both DialogueState and FlowContext
            flow_stack = state.get("flow_stack", []).copy()
            if flow_stack:
                flow_stack[-1] = {**flow_stack[-1], "current_step": target_step}

            # Set waiting_for_slot if we're in a collect step with a next slot
            waiting_for_slot = None
            if target_step_config.type == "collect":
                next_slot = step_manager.get_next_required_slot(
                    {**state, "flow_slots": flow_slots, "current_step": target_step},
                    target_step_config,
                    runtime.context,
                )
                if next_slot:
                    waiting_for_slot = next_slot

            logger.info(
                f"Correction detected: returning to step '{target_step}' "
                f"(previous was '{previous_step}') with state '{new_conversation_state}'"
            )

            # CRITICAL: Clear user_message after processing to prevent routing loops
            # The user_message has been processed (slot corrected), so it should not
            # trigger another understand cycle when collect_next_slot runs
            result = {
                "flow_slots": flow_slots,
                "conversation_state": new_conversation_state,
                "current_step": target_step,
                "flow_stack": flow_stack,
                "metadata": metadata,
                "last_response": last_response,
                "user_message": "",  # Clear to prevent loops
            }

            if waiting_for_slot:
                result["waiting_for_slot"] = waiting_for_slot

            return result

    # Fallback: just update slot and stay in current state
    logger.warning("Could not determine target step for correction, staying in current state")
    # Get acknowledgment message using template (Task 005)
    config = runtime.context["config"]
    logger.info(
        f"handle_correction (fallback): Generating acknowledgment for slot '{slot_name}' "
        f"with new value '{normalized_value}'"
    )
    acknowledgment = _get_response_template(
        config,
        "correction_acknowledged",
        "Got it, I've updated {slot_name} to {new_value}.",
        slot_name=slot_name,
        new_value=normalized_value,
    )
    logger.info(f"handle_correction (fallback): Generated acknowledgment: '{acknowledgment}'")
    # CRITICAL: Clear user_message after processing to prevent routing loops
    return {
        "flow_slots": flow_slots,
        "conversation_state": previous_conversation_state or "waiting_for_slot",
        "metadata": metadata,
        "last_response": acknowledgment,
        "user_message": "",  # Clear to prevent loops
    }


def _get_response_template(
    config: Any,
    template_name: str,
    default_template: str,
    **kwargs: Any,
) -> str:
    """
    Get response template from config and interpolate variables.

    Args:
        config: SoniConfig instance
        template_name: Name of template in config.responses (if it exists)
        default_template: Default template if not found
        **kwargs: Variables to interpolate (e.g., slot_name="origin", new_value="NYC")

    Returns:
        Interpolated template string
    """
    template = None
    # Check if config has responses field (may not be implemented yet)
    if hasattr(config, "responses") and config.responses:
        template_config = config.responses.get(template_name)
        if template_config:
            # Use default or first variation
            if isinstance(template_config, dict):
                template = template_config.get("default")
            elif isinstance(template_config, str):
                template = template_config
            logger.debug(
                f"_get_response_template: Found template '{template_name}' in config: '{template}'"
            )

    if not template:
        template = default_template
        logger.debug(
            f"_get_response_template: Using default template for '{template_name}': '{template}'"
        )

    # Interpolate variables
    result = template
    for key, value in kwargs.items():
        result = result.replace(f"{{{key}}}", str(value))

    logger.debug(
        f"_get_response_template: Interpolated template '{template_name}': '{result}' "
        f"with kwargs: {kwargs}"
    )

    return result
