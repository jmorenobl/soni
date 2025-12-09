"""Flow step progression manager for Soni Framework.

This module provides FlowStepManager class that handles sequential step execution
according to the flow definition in YAML configuration.
"""

import logging
from typing import Any

from soni.core.config import SoniConfig, StepConfig
from soni.core.state import (
    DialogueState,
    RuntimeContext,
    get_all_slots,
    get_flow_config,
)
from soni.core.types import FlowContext

logger = logging.getLogger(__name__)


class FlowStepManager:
    """Manages flow step progression and tracking.

    Responsibilities:
    - Track current step in flow execution
    - Determine next step based on flow definition
    - Check if step is complete (all slots collected)
    - Get step configuration from flow definition

    This class follows Single Responsibility Principle (SRP) by encapsulating
    all step progression logic in one place.
    """

    def __init__(self, config: SoniConfig) -> None:
        """Initialize FlowStepManager with configuration.

        Args:
            config: Soni configuration containing flow definitions
        """
        self.config = config

    def get_current_step_config(
        self,
        state: DialogueState,
        context: RuntimeContext,
    ) -> StepConfig | None:
        """Get configuration for current step.

        Args:
            state: Current dialogue state
            context: Runtime context with dependencies

        Returns:
            StepConfig for current step, or None if no current step
        """
        # Get active flow context
        flow_stack = state.get("flow_stack", [])
        if not flow_stack:
            return None

        active_ctx: FlowContext = flow_stack[-1]
        current_step_name = active_ctx.get("current_step")

        if not current_step_name:
            return None

        # Get flow configuration
        flow_name = active_ctx["flow_name"]
        try:
            flow_config = get_flow_config(context, flow_name)
        except KeyError:
            logger.warning(f"Flow '{flow_name}' not found in configuration")
            return None

        # Find step in flow definition
        steps: list[StepConfig] = flow_config.steps_or_process
        for step in steps:
            if step.step == current_step_name:
                return step

        logger.warning(f"Step '{current_step_name}' not found in flow '{flow_name}'")
        return None

    def get_next_step_config(
        self,
        state: DialogueState,
        context: RuntimeContext,
    ) -> StepConfig | None:
        """Get configuration for next step in sequence.

        Args:
            state: Current dialogue state
            context: Runtime context with dependencies

        Returns:
            StepConfig for next step, or None if no next step (flow complete)
        """
        # Get active flow context
        flow_stack = state.get("flow_stack", [])
        if not flow_stack:
            return None

        active_ctx: FlowContext = flow_stack[-1]
        current_step_name = active_ctx.get("current_step")
        flow_name = active_ctx["flow_name"]

        # Get flow configuration
        try:
            flow_config = get_flow_config(context, flow_name)
        except KeyError:
            logger.warning(f"Flow '{flow_name}' not found in configuration")
            return None

        steps: list[StepConfig] = flow_config.steps_or_process
        if not steps:
            return None

        # If no current step, return first step
        if not current_step_name:
            return steps[0]

        # Find current step index
        current_index: int | None = None
        for i, step in enumerate(steps):
            if step.step == current_step_name:
                current_index = i
                break

        if current_index is None:
            # Current step not found, return first step
            logger.warning(
                f"Current step '{current_step_name}' not found in flow '{flow_name}', "
                "returning first step"
            )
            return steps[0]

        # Return next step if exists
        if current_index + 1 < len(steps):
            return steps[current_index + 1]

        # No next step - flow is complete
        return None

    def advance_to_next_step(
        self,
        state: DialogueState,
        context: RuntimeContext,
    ) -> dict[str, Any]:
        """Advance to next step and update state.

        Args:
            state: Current dialogue state (will be mutated)
            context: Runtime context with dependencies

        Returns:
            State updates dict with:
            - current_step: Updated step name or None if flow complete
            - conversation_state: Updated based on next step type
        """
        next_step = self.get_next_step_config(state, context)

        # Update current_step in FlowContext
        flow_stack = state.get("flow_stack", [])
        if flow_stack:
            active_ctx = flow_stack[-1]
            if next_step:
                active_ctx["current_step"] = next_step.step
            else:
                active_ctx["current_step"] = None

        # Determine conversation_state based on next step type
        if not next_step:
            # Flow complete - mark as completed but DON'T pop yet
            # The generate_response_node will pop after generating final response
            if flow_stack:
                flow_stack[-1]["flow_state"] = "completed"

            return {
                "flow_stack": flow_stack,
                "conversation_state": "completed",
            }

        # Set conversation_state based on step type
        step_type = next_step.type
        if step_type == "action":
            conversation_state = "ready_for_action"
        elif step_type == "collect":
            conversation_state = "waiting_for_slot"
        elif step_type == "confirm":
            conversation_state = "ready_for_confirmation"
        elif step_type == "branch":
            # Branch steps don't have a specific waiting state
            conversation_state = "understanding"
        elif step_type == "say":
            # Say steps just generate response
            conversation_state = "generating_response"
        else:
            # Default to waiting_for_slot for unknown types
            conversation_state = "waiting_for_slot"

        return {
            "flow_stack": flow_stack,
            "conversation_state": conversation_state,
        }

    def is_step_complete(
        self,
        state: DialogueState,
        step_config: StepConfig,
        context: RuntimeContext,
    ) -> bool:
        """Check if current step has all required slots.

        For collect steps, checks if the slot is filled.
        For action and confirm steps, always returns False (they need to be executed).

        Args:
            state: Current dialogue state
            step_config: Configuration for current step
            context: Runtime context with dependencies

        Returns:
            True if step is complete, False otherwise
        """
        # Action and confirm steps are never "pre-completed" - they execute when reached
        if step_config.type in ("action", "confirm"):
            return False

        # Only collect steps can be "complete" (slot filled)
        if step_config.type != "collect":
            # Other step types (branch, say) are considered complete for advancement
            return True

        # For collect steps, check if slot is filled
        if not step_config.slot:
            logger.warning(f"Collect step '{step_config.step}' has no slot defined")
            return False

        slot_name = step_config.slot
        slots = get_all_slots(state)

        # Check if slot is filled (not None and not empty string)
        slot_value = slots.get(slot_name)
        is_filled = (
            slot_value is not None
            and slot_value != ""
            and (not isinstance(slot_value, str) or slot_value.strip() != "")
        )

        return is_filled

    def get_next_required_slot(
        self,
        state: DialogueState,
        step_config: StepConfig,
        context: RuntimeContext,
    ) -> str | None:
        """Get next slot to collect for current step.

        Args:
            state: Current dialogue state
            step_config: Configuration for current step
            context: Runtime context with dependencies

        Returns:
            Slot name if step is collect type and slot is not filled, None otherwise
        """
        # Only collect steps have slots
        if step_config.type != "collect":
            return None

        if not step_config.slot:
            return None

        slot_name = step_config.slot

        # Check if slot is already filled
        if self.is_step_complete(state, step_config, context):
            return None

        return slot_name

    def advance_through_completed_steps(
        self,
        state: DialogueState,
        context: RuntimeContext,
    ) -> dict[str, Any]:
        """Advance through all completed steps until finding an incomplete one.

        This function iteratively checks if the current step is complete and advances
        to the next step until it finds a step that is not complete, or until the flow
        is finished.

        Critical for handling cases where multiple slots are provided in one message.

        Args:
            state: Current dialogue state (will be mutated in-place)
            context: Runtime context with dependencies

        Returns:
            State updates dict with:
            - current_step: Final step name or None if flow complete
            - conversation_state: Updated based on final step type
            - flow_stack: Updated flow stack
            - waiting_for_slot: Updated if final step is collect type
            - current_prompted_slot: Updated if final step is collect type
            - all_slots_filled: True when all slots are filled and at action/confirm step

        Example:
            >>> # User provides origin and destination in one message
            >>> # After saving slots, call this method
            >>> updates = step_manager.advance_through_completed_steps(state, context)
            >>> # Will advance through collect_origin and collect_destination
            >>> # Stop at collect_date (incomplete)
            >>> assert updates["current_step"] == "collect_date"
            >>> assert updates["waiting_for_slot"] == "departure_date"
        """
        max_iterations = 20  # Safety limit to prevent infinite loops
        iterations = 0
        flow_manager = context["flow_manager"]

        while iterations < max_iterations:
            iterations += 1

            # Get active flow context
            active_ctx = flow_manager.get_active_context(state)
            if not active_ctx:
                logger.warning("No active flow in advance_through_completed_steps")
                return {"conversation_state": "idle"}

            flow_name = active_ctx["flow_name"]

            # Get current step configuration
            current_step_config = self.get_current_step_config(state, context)

            # If no current step, try to start at first step
            if not current_step_config:
                # Try to get first step from flow config
                try:
                    flow_config = get_flow_config(context, flow_name)
                    if flow_config and flow_config.steps_or_process:
                        first_step = flow_config.steps_or_process[0]
                        # Update flow context to first step
                        if state["flow_stack"]:
                            state["flow_stack"][-1]["current_step"] = first_step.step
                        current_step_config = first_step
                    else:
                        # No steps in flow - mark as completed
                        logger.info(f"Flow {flow_name} has no steps, marking as completed")
                        flow_manager.pop_flow(state, result="completed")
                        return {
                            "conversation_state": "completed",
                            "all_slots_filled": True,
                            "current_step": None,
                        }
                except KeyError:
                    logger.error(f"Flow '{flow_name}' not found in configuration")
                    return {"conversation_state": "error"}

            if not current_step_config:
                # Truly no step - flow complete
                logger.info(f"Flow {flow_name} complete after {iterations} iteration(s)")
                flow_manager.pop_flow(state, result="completed")
                return {
                    "conversation_state": "completed",
                    "all_slots_filled": True,
                    "current_step": None,
                }

            # Check if current step is complete
            is_complete = self.is_step_complete(state, current_step_config, context)

            if is_complete:
                # Step complete - advance to next step
                logger.debug(
                    f"Step '{current_step_config.step}' is complete, advancing... "
                    f"(iteration {iterations})"
                )

                advance_updates = self.advance_to_next_step(state, context)

                # Check if flow is complete (no next step)
                if advance_updates.get("conversation_state") == "completed":
                    logger.info(f"Flow completed after {iterations} iteration(s)")
                    flow_manager.pop_flow(state, result="completed")
                    return {
                        **advance_updates,
                        "all_slots_filled": True,
                    }

                # Update state for next iteration
                from typing import cast

                state_dict = cast(dict[str, Any], state)
                state_dict.update(advance_updates)

            else:
                # Found incomplete step - determine conversation state
                step_type = current_step_config.type
                logger.info(
                    f"Stopped at incomplete step '{current_step_config.step}' "
                    f"(type={step_type}) after {iterations} iteration(s)"
                )

                updates: dict[str, Any] = {
                    "flow_stack": state.get("flow_stack", []),
                }

                # Determine conversation_state and set all_slots_filled
                if step_type == "action":
                    updates["conversation_state"] = "ready_for_action"
                    updates["all_slots_filled"] = True
                    updates["waiting_for_slot"] = None
                elif step_type == "confirm":
                    updates["conversation_state"] = "ready_for_confirmation"
                    updates["all_slots_filled"] = True
                    updates["waiting_for_slot"] = None
                elif step_type == "collect":
                    updates["conversation_state"] = "waiting_for_slot"
                    updates["all_slots_filled"] = False
                    if current_step_config.slot:
                        updates["waiting_for_slot"] = current_step_config.slot
                        updates["current_prompted_slot"] = current_step_config.slot
                else:
                    # Default for other step types
                    step_type_to_state = {
                        "branch": "understanding",
                        "say": "generating_response",
                    }
                    updates["conversation_state"] = step_type_to_state.get(
                        step_type, "understanding"
                    )
                    updates["all_slots_filled"] = False

                return updates

        # Max iterations reached
        logger.error(
            f"Max iterations ({max_iterations}) reached in advance_through_completed_steps"
        )
        return {"conversation_state": "error"}
