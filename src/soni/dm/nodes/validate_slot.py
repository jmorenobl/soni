"""Validate slot node for slot validation and normalization."""

import logging
from typing import Any

from soni.core.types import DialogueState, FlowContext, NodeRuntime

logger = logging.getLogger(__name__)


async def _process_all_slots(
    slots: list,
    state: DialogueState,
    active_ctx: FlowContext,
    normalizer: Any,  # INormalizer - using Any to avoid import issues
) -> dict[str, dict[str, Any]]:
    """Process and normalize all slots from NLU result.

    This function handles multiple slot formats (dict, SlotValue model, string)
    and normalizes all slot values before saving them to state.

    Args:
        slots: List of slots from NLU result. Can contain:
            - dict: {"name": "origin", "value": "New York"}
            - SlotValue: SlotValue(name="origin", value="New York")
            - str: Raw string value (uses waiting_for_slot as name)
        state: Current dialogue state
        active_ctx: Active flow context containing flow_id
        normalizer: Slot normalizer for value normalization

    Returns:
        Dictionary of flow_slots structure:
        {
            flow_id: {
                slot_name: normalized_value,
                ...
            }
        }

    Example:
        >>> slots = [
        ...     {"name": "origin", "value": "New York"},
        ...     {"name": "destination", "value": "Los Angeles"},
        ... ]
        >>> flow_slots = await _process_all_slots(slots, state, active_ctx, normalizer)
        >>> assert flow_slots[flow_id]["origin"] == "New York"
        >>> assert flow_slots[flow_id]["destination"] == "Los Angeles"
    """
    flow_id = active_ctx["flow_id"]
    flow_slots = state.get("flow_slots", {}).copy()
    if flow_id not in flow_slots:
        flow_slots[flow_id] = {}

    for slot in slots:
        # Extract slot info
        if hasattr(slot, "name"):
            slot_name = slot.name
            raw_value = slot.value
        elif isinstance(slot, dict):
            slot_name = slot.get("name")
            raw_value = slot.get("value")
        elif isinstance(slot, str):
            slot_name = state.get("waiting_for_slot")
            raw_value = slot
        else:
            logger.warning(f"Unknown slot format: {type(slot)}, skipping")
            continue

        if not slot_name:
            logger.warning(f"Slot has no name, skipping: {slot}")
            continue

        # Normalize slot value
        normalized_value = await normalizer.normalize_slot(slot_name, raw_value)
        flow_slots[flow_id][slot_name] = normalized_value

        logger.debug(f"Processed slot '{slot_name}' = '{normalized_value}'")

    return flow_slots


def _detect_correction_or_modification(
    slots: list,
    message_type: str,
) -> bool:
    """Detect if message is a correction or modification.

    Args:
        slots: List of slots from NLU result
        message_type: Message type from NLU result

    Returns:
        True if this is a correction or modification, False otherwise
    """
    # Check if this is a fallback slot (created when NLU didn't extract)
    # Fallback slots have action=PROVIDE and confidence=0.5
    is_fallback_slot = (
        len(slots) == 1
        and isinstance(slots[0], dict)
        and slots[0].get("action") == "provide"
        and slots[0].get("confidence", 1.0) == 0.5
    )

    # Check slot actions - a slot with CORRECT or MODIFY action indicates correction/modification
    slot_actions = [
        slot.get("action") if isinstance(slot, dict) else getattr(slot, "action", None)
        for slot in slots
    ]
    has_correct_or_modify_action = any(
        action in ("correct", "modify", "CORRECT", "MODIFY") for action in slot_actions if action
    )

    # Fallback slots should NEVER be treated as corrections/modifications
    is_correction_or_modification = not is_fallback_slot and (
        message_type in ("correction", "modification") or has_correct_or_modify_action
    )

    return is_correction_or_modification


def _handle_correction_flow(
    state: DialogueState,
    runtime: NodeRuntime,
    flow_slots: dict[str, dict[str, Any]],
    previous_step: str | None,
) -> dict[str, Any]:
    """Handle correction/modification flow.

    This function preserves the existing correction handling logic, determining
    which step to return to and updating the conversation state accordingly.

    Args:
        state: Current dialogue state
        runtime: Runtime context
        flow_slots: Updated flow slots
        previous_step: Previous step name before correction

    Returns:
        State updates for correction flow
    """
    step_manager = runtime.context["step_manager"]
    flow_manager = runtime.context["flow_manager"]
    active_ctx = flow_manager.get_active_context(state)

    if not active_ctx:
        return {"conversation_state": "error"}

    previous_conversation_state = state.get("conversation_state")

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
        flow_id = active_ctx["flow_id"]
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
    # We need to get the slot name from flow_slots - find the last updated slot
    if not target_step and flow_config and flow_config.steps:
        flow_id = active_ctx["flow_id"]
        current_slots = flow_slots.get(flow_id, {})
        # Get the slot name from the last slot in the list (most recent)
        # This is a fallback, so we'll use the first collect step for this slot
        for step in flow_config.steps:
            if step.type == "collect" and step.slot in current_slots:
                target_step = step.step
                break

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

    # If no target step found, return error
    logger.warning(
        f"Could not determine target step for correction. "
        f"previous_step={previous_step}, flow_config={flow_config is not None}"
    )
    return {"conversation_state": "error"}


async def validate_slot_node(
    state: DialogueState,
    runtime: NodeRuntime,
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
            # Flow is active but no slots extracted
            waiting_for_slot = state.get("waiting_for_slot")

            # FALLBACK: If message_type is slot_value and we're waiting for a slot,
            # try to extract the value using a more specific NLU call
            # ONLY use fallback when we're in a collect step (not in initial flow activation)
            current_step = active_ctx.get("current_step")
            if message_type == "slot_value" and waiting_for_slot and current_step:
                user_message = state.get("user_message", "")
                if user_message and user_message.strip():
                    # NLU classified as slot_value but didn't extract the slot
                    # This can happen when the value is clear but NLU didn't associate it
                    # FALLBACK: Make a second NLU call with more specific context
                    logger.info(
                        f"FALLBACK: NLU didn't extract slot '{waiting_for_slot}' from message "
                        f"'{user_message}'. Making second NLU call with specific context."
                    )

                    try:
                        # Get NLU provider and make a second call with focused context
                        nlu_provider = runtime.context["nlu_provider"]

                        import dspy

                        from soni.du.models import DialogueContext

                        # Create a focused context with only the expected slot
                        # This helps the NLU focus on extracting just this one slot
                        scope_manager = runtime.context["scope_manager"]
                        available_actions = scope_manager.get_available_actions(state)
                        available_flows = scope_manager.get_available_flows(state)

                        focused_context = DialogueContext(
                            current_slots=state.get("flow_slots", {}).get(
                                active_ctx["flow_id"], {}
                            ),
                            available_actions=available_actions,
                            available_flows=available_flows,
                            current_flow=active_ctx["flow_name"],
                            expected_slots=[waiting_for_slot],  # Only the slot we're waiting for
                            current_prompted_slot=waiting_for_slot,
                        )

                        # Get conversation history
                        messages = state.get("messages", [])
                        history = dspy.History()
                        for msg in messages[-5:]:  # Last 5 messages for context
                            if hasattr(msg, "content"):
                                if hasattr(msg, "role") and msg.role == "user":
                                    history.add_user_message(msg.content)
                                elif hasattr(msg, "role") and msg.role == "assistant":
                                    history.add_assistant_message(msg.content)

                        # Make focused NLU call
                        fallback_result = await nlu_provider.predict(
                            user_message=user_message,
                            history=history,
                            context=focused_context,
                        )

                        # CRITICAL: Verify that the fallback call also classified as slot_value
                        # If it classified as digression/question/etc, don't extract slot
                        fallback_message_type = fallback_result.message_type
                        if hasattr(fallback_message_type, "value"):
                            fallback_message_type = fallback_message_type.value
                        fallback_message_type = str(fallback_message_type).lower()

                        if fallback_message_type != "slot_value":
                            # Fallback NLU call classified as something else (digression, question, etc)
                            # Don't extract slot - this is likely a digression, not a slot value
                            logger.info(
                                f"FALLBACK: Second NLU call classified as '{fallback_message_type}' "
                                f"instead of 'slot_value'. This appears to be a digression, not a slot value. "
                                f"Not extracting slot."
                            )
                            # Don't create a fallback slot - let normal error handling proceed
                            # This will generate a response asking the user to clarify
                        else:
                            # Fallback call also classified as slot_value - safe to extract
                            # Check if the focused call extracted the slot
                            fallback_slots = fallback_result.slots or []
                            extracted_slot = None
                            for slot in fallback_slots:
                                if (hasattr(slot, "name") and slot.name == waiting_for_slot) or (
                                    isinstance(slot, dict) and slot.get("name") == waiting_for_slot
                                ):
                                    extracted_slot = slot
                                    break

                            if extracted_slot:
                                # Success! Use the extracted slot
                                if hasattr(extracted_slot, "model_dump"):
                                    slots = [extracted_slot.model_dump(mode="json")]
                                elif isinstance(extracted_slot, dict):
                                    slots = [extracted_slot]
                                else:
                                    # Convert to dict format
                                    from soni.du.models import SlotAction, SlotValue

                                    # Convert action string to SlotAction enum
                                    action_value = (
                                        extracted_slot.action
                                        if hasattr(extracted_slot, "action")
                                        else SlotAction.PROVIDE
                                    )
                                    if isinstance(action_value, str):
                                        try:
                                            action_enum = SlotAction(action_value.lower())
                                        except ValueError:
                                            action_enum = SlotAction.PROVIDE
                                    else:
                                        action_enum = action_value

                                    slots = [
                                        SlotValue(
                                            name=waiting_for_slot,
                                            value=(
                                                extracted_slot.value
                                                if hasattr(extracted_slot, "value")
                                                else str(extracted_slot)
                                            ),
                                            confidence=(
                                                extracted_slot.confidence
                                                if hasattr(extracted_slot, "confidence")
                                                else 0.7
                                            ),
                                            action=action_enum,
                                        ).model_dump(mode="json")
                                    ]
                                logger.info(
                                    f"FALLBACK SUCCESS: Second NLU call extracted slot '{waiting_for_slot}' "
                                    f"with value '{slots[0].get('value') if isinstance(slots[0], dict) else slots[0].value}'"
                                )
                            else:
                                # Even the focused call didn't extract it - this is unusual
                                # Log warning but don't use fallback (let normal error handling proceed)
                                logger.warning(
                                    f"FALLBACK FAILED: Even focused NLU call didn't extract slot "
                                    f"'{waiting_for_slot}' from message '{user_message}'. "
                                    f"This may indicate the message doesn't contain the expected value."
                                )
                            # Don't create a fallback slot - let normal error handling proceed
                            # This will generate a response asking the user to clarify

                    except Exception as e:
                        # If fallback NLU call fails, log and let normal error handling proceed
                        logger.error(
                            f"FALLBACK ERROR: Failed to make second NLU call: {e}. "
                            f"Falling back to normal error handling."
                        )
                else:
                    # No user message - can't use fallback
                    logger.warning(
                        f"FALLBACK: Cannot use fallback - no user_message available. "
                        f"message_type={message_type}, waiting_for_slot={waiting_for_slot}"
                    )

            # If still no slots after fallback attempt, handle as before
            if not slots:
                if waiting_for_slot:
                    # Already waiting for a slot - generate a response asking for it again
                    # CRITICAL: Use "idle" state to break the loop - this will route to generate_response
                    # instead of going back to collect_next_slot
                    logger.warning(
                        f"Already waiting for slot '{waiting_for_slot}' but no slots extracted "
                        f"(even after fallback). Generating response to ask again and breaking loop."
                    )
                    # Get slot config for better prompt
                    from soni.core.state import get_slot_config

                    try:
                        slot_config = get_slot_config(runtime.context, waiting_for_slot)
                        prompt = (
                            slot_config.prompt
                            if hasattr(slot_config, "prompt")
                            else f"Please provide your {waiting_for_slot}."
                        )
                    except KeyError:
                        prompt = f"Please provide your {waiting_for_slot}."

                    return {
                        "conversation_state": "idle",  # Use "idle" to route to generate_response
                        "last_response": (f"I didn't understand your response. {prompt}"),
                    }
                # Not waiting for a slot yet - continue to collect next slot
                return {"conversation_state": "waiting_for_slot"}
        else:
            # No flow active - this is an error state
            return {"conversation_state": "error"}

    # Get flow manager and active context
    flow_manager = runtime.context["flow_manager"]
    step_manager = runtime.context["step_manager"]
    active_ctx = flow_manager.get_active_context(state)

    if not active_ctx:
        return {"conversation_state": "error"}

    # Step 1: Capture current step BEFORE updating slot
    # This is critical for corrections/modifications to return to the correct step
    previous_step = active_ctx.get("current_step")

    # Step 2: Detect if this is a correction or modification
    message_type = nlu_result.get("message_type", "")
    is_correction_or_modification = _detect_correction_or_modification(slots, message_type)

    logger.debug(
        f"validate_slot: message_type={message_type}, "
        f"previous_step={previous_step}, is_correction_or_modification={is_correction_or_modification}"
    )

    # Process all slots using helper
    try:
        flow_slots = await _process_all_slots(slots, state, active_ctx, normalizer)
        state["flow_slots"] = flow_slots

        # Step 3: If correction/modification, return to previous step instead of advancing
        if is_correction_or_modification:
            return _handle_correction_flow(state, runtime, flow_slots, previous_step)

        # Normal flow: Advance through completed steps
        updates: dict[str, Any] = dict(
            step_manager.advance_through_completed_steps(state, runtime.context)
        )
        updates["flow_slots"] = flow_slots

        # CRITICAL: Clear user_message after processing to prevent routing loops
        # The user_message has been processed (slot validated), so it should not
        # trigger another understand cycle when collect_next_slot runs
        updates["user_message"] = ""

        # DEBUG: Log what validate_slot is returning
        logger.info("=" * 80)
        logger.info("validate_slot: COMPLETED SLOT VALIDATION")
        logger.info(f"  Cleared user_message (was: '{state.get('user_message')}')")
        logger.info(f"  Updated flow_slots: {updates.get('flow_slots', {})}")
        logger.info(f"  conversation_state: {updates.get('conversation_state')}")
        logger.info(f"  current_step: {updates.get('current_step')}")
        logger.info("  CRITICAL: last_response NOT updated by validate_slot")
        logger.info("  Next node (collect_next_slot) should update last_response")
        logger.info("=" * 80)

        return updates

    except Exception as e:
        logger.error(f"Validation failed: {e}")
        return {
            "conversation_state": "error",
            "validation_error": str(e),
        }
