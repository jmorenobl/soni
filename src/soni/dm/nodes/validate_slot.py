"""Validate slot node for slot validation and normalization (v2.0 Command-Driven)."""

import logging
from typing import Any

from soni.core.commands import Command, CorrectSlot, SetSlot
from soni.core.types import DialogueState, FlowContext, NodeRuntime

logger = logging.getLogger(__name__)


def _extract_slot_commands(commands: list[Command]) -> tuple[list[SetSlot], list[CorrectSlot]]:
    """Extract SetSlot and CorrectSlot commands from NLU result.

    Args:
        commands: List of commands from NLU result

    Returns:
        Tuple of (set_slot_commands, correct_slot_commands)
    """
    set_slots: list[SetSlot] = []
    correct_slots: list[CorrectSlot] = []

    for cmd in commands:
        if isinstance(cmd, SetSlot):
            set_slots.append(cmd)
        elif isinstance(cmd, CorrectSlot):
            correct_slots.append(cmd)

    return set_slots, correct_slots


async def _process_slot_commands(
    set_slots: list[SetSlot],
    correct_slots: list[CorrectSlot],
    state: DialogueState,
    active_ctx: FlowContext,
    normalizer: Any,
) -> tuple[dict[str, dict[str, Any]], bool]:
    """Process SetSlot and CorrectSlot commands.

    Args:
        set_slots: List of SetSlot commands
        correct_slots: List of CorrectSlot commands
        state: Current dialogue state
        active_ctx: Active flow context
        normalizer: Slot normalizer

    Returns:
        Tuple of (updated flow_slots, is_correction)
    """
    flow_id = active_ctx["flow_id"]
    flow_slots = state.get("flow_slots", {}).copy()
    if flow_id not in flow_slots:
        flow_slots[flow_id] = {}

    is_correction = len(correct_slots) > 0

    # Process SetSlot commands
    for cmd in set_slots:
        normalized_value = await normalizer.normalize_slot(cmd.slot_name, cmd.value)
        flow_slots[flow_id][cmd.slot_name] = normalized_value
        logger.debug(f"SetSlot: '{cmd.slot_name}' = '{normalized_value}'")

    # Process CorrectSlot commands
    for cmd in correct_slots:
        normalized_value = await normalizer.normalize_slot(cmd.slot_name, cmd.new_value)
        flow_slots[flow_id][cmd.slot_name] = normalized_value
        logger.debug(f"CorrectSlot: '{cmd.slot_name}' = '{normalized_value}'")

    return flow_slots, is_correction


def _handle_correction_flow(
    state: DialogueState,
    runtime: NodeRuntime,
    flow_slots: dict[str, dict[str, Any]],
    previous_step: str | None,
) -> dict[str, Any]:
    """Handle correction/modification flow.

    This function determines which step to return to after a correction
    and updates the conversation state accordingly.

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

    # Check if all required slots are filled
    flow_config = step_manager.config.flows.get(active_ctx["flow_name"])
    all_slots_filled = False
    if flow_config:
        required_slots = set()
        for step in flow_config.steps:
            if step.type == "collect" and step.slot:
                required_slots.add(step.slot)

        flow_id = active_ctx["flow_id"]
        filled_slots = set(flow_slots[flow_id].keys())
        all_slots_filled = required_slots.issubset(filled_slots)

        logger.debug(
            f"Correction check: required_slots={required_slots}, "
            f"filled_slots={filled_slots}, all_slots_filled={all_slots_filled}"
        )

    # If all slots are filled, return to confirmation/action step
    if all_slots_filled and flow_config and flow_config.steps:
        for step in reversed(flow_config.steps):
            if step.type in ("confirm", "action"):
                target_step = step.step
                logger.debug(
                    f"All slots filled, returning to last step '{target_step}' "
                    f"instead of '{previous_step}'"
                )
                break

    # Handle special case for confirmation state
    if (
        target_step
        and previous_conversation_state
        in ("ready_for_action", "ready_for_confirmation", "executing_action", "confirming")
        and flow_config
        and flow_config.steps
    ):
        for step in reversed(flow_config.steps):
            if previous_conversation_state in ("ready_for_confirmation", "confirming"):
                if step.type == "confirm":
                    target_step = step.step
                    break
            elif previous_conversation_state in ("ready_for_action", "executing_action"):
                if step.type == "action":
                    target_step = step.step
                    break

    # Fallback: find step that collects the corrected slot
    if not target_step and flow_config and flow_config.steps:
        flow_id = active_ctx["flow_id"]
        current_slots = flow_slots.get(flow_id, {})
        for step in flow_config.steps:
            if step.type == "collect" and step.slot in current_slots:
                target_step = step.step
                break

    if target_step:
        # Get the target step configuration
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

            if target_step_config.type == "confirm":
                new_conversation_state = "ready_for_confirmation"

            # Update flow stack with new current_step
            flow_stack = state.get("flow_stack", []).copy()
            if flow_stack:
                flow_stack[-1] = {**flow_stack[-1], "current_step": target_step}

            logger.info(
                f"Correction detected: returning to step '{target_step}' "
                f"(previous was '{previous_step}') with state '{new_conversation_state}'"
            )

            return {
                "flow_slots": flow_slots,
                "conversation_state": new_conversation_state,
                "current_step": target_step,
                "flow_stack": flow_stack,
            }

    logger.warning(
        f"Could not determine target step for correction. "
        f"previous_step={previous_step}, flow_config={flow_config is not None}"
    )
    return {"conversation_state": "error"}


async def validate_slot_node(
    state: DialogueState,
    runtime: NodeRuntime,
) -> dict:
    """Validate and normalize slot values from NLU commands.

    This node extracts SetSlot and CorrectSlot commands from the NLU result,
    normalizes the values, and updates the flow_slots state.

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

    # Extract commands from NLU result
    commands = nlu_result.get("commands", [])

    # Handle case where commands are dicts (serialized) vs Command objects
    parsed_commands: list[Command] = []
    for cmd in commands:
        if isinstance(cmd, Command):
            parsed_commands.append(cmd)
        elif isinstance(cmd, dict):
            # Reconstruct Command from dict
            cmd_type = cmd.get("type") or cmd.get("__class__")
            if cmd_type == "SetSlot" or (hasattr(cmd, "slot_name") and hasattr(cmd, "value")):
                parsed_commands.append(
                    SetSlot(slot_name=cmd.get("slot_name", ""), value=cmd.get("value", ""))
                )
            elif cmd_type == "CorrectSlot" or (
                hasattr(cmd, "slot_name") and hasattr(cmd, "new_value")
            ):
                parsed_commands.append(
                    CorrectSlot(
                        slot_name=cmd.get("slot_name", ""), new_value=cmd.get("new_value", "")
                    )
                )

    set_slots, correct_slots = _extract_slot_commands(parsed_commands)

    if not set_slots and not correct_slots:
        logger.warning("No SetSlot or CorrectSlot commands in NLU result")
        # No slot commands - continue to collect next slot
        return {"conversation_state": "waiting_for_slot"}

    # Get flow manager and active context
    flow_manager = runtime.context["flow_manager"]
    step_manager = runtime.context["step_manager"]
    active_ctx = flow_manager.get_active_context(state)

    if not active_ctx:
        return {"conversation_state": "error"}

    # Capture current step BEFORE updating slots (for correction handling)
    previous_step = active_ctx.get("current_step")

    # Process slot commands
    try:
        flow_slots, is_correction = await _process_slot_commands(
            set_slots, correct_slots, state, active_ctx, normalizer
        )
        state["flow_slots"] = flow_slots

        # If correction, return to appropriate step
        if is_correction:
            return _handle_correction_flow(state, runtime, flow_slots, previous_step)

        # Normal flow: Advance through completed steps
        updates: dict[str, Any] = dict(
            step_manager.advance_through_completed_steps(state, runtime.context)
        )
        updates["flow_slots"] = flow_slots

        # Clear user_message after processing to prevent routing loops
        updates["user_message"] = ""

        logger.info("=" * 80)
        logger.info("validate_slot: COMPLETED SLOT VALIDATION")
        logger.info(f"  Cleared user_message (was: '{state.get('user_message')}')")
        logger.info(f"  Updated flow_slots: {updates.get('flow_slots', {})}")
        logger.info(f"  conversation_state: {updates.get('conversation_state')}")
        logger.info(f"  current_step: {updates.get('current_step')}")
        logger.info("=" * 80)

        return updates

    except Exception as e:
        logger.error(f"Validation failed: {e}")
        return {
            "conversation_state": "error",
            "validation_error": str(e),
        }
