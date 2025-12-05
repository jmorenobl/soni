"""Routing logic for dialogue flows"""

import logging
from collections.abc import Callable
from typing import Any, Literal

from soni.core.events import EVENT_SLOT_COLLECTION, EVENT_VALIDATION_ERROR
from soni.core.state import DialogueState, get_slot, state_from_dict
from soni.core.types import DialogueState as DialogueStateType

logger = logging.getLogger(__name__)


def should_continue(state: DialogueState | dict[str, Any]) -> str:
    """
    Determine next step after understanding.

    Args:
        state: Current dialogue state

    Returns:
        Next node name

    Note:
        This is a placeholder for future routing logic.
        Currently, flows are linear and routing is handled by DAG edges.
    """
    # state_from_dict expects dict only, so check type first
    if not isinstance(state, dict):
        # Already DialogueState (TypedDict)
        pass

    # For linear flows, routing is handled by sequential edges
    # This function is reserved for future conditional routing
    return "continue"


def route_by_intent(state: DialogueState | dict[str, Any]) -> str:
    """
    Route to flow based on intent.

    Args:
        state: Current dialogue state

    Returns:
        Flow name to route to

    Note:
        This is a placeholder for future intent-based routing.
    """
    # state_from_dict expects dict only, so check type first
    if not isinstance(state, dict):
        # Already DialogueState (TypedDict)
        pass

    # Placeholder for future intent-based routing
    # For now, flows are explicitly called
    return "fallback"


def create_branch_router(
    input_var: str, cases: dict[str, str]
) -> Callable[[DialogueState | dict[str, Any]], str]:
    """
    Create a branch router function that routes based on state variable value.

    Args:
        input_var: Name of state variable to evaluate (from slots)
        cases: Mapping of case values to target step names

    Returns:
        Router function that takes state and returns target step name

    Example:
        >>> state = create_empty_state()
        >>> push_flow(state, "test_flow")
        >>> set_slot(state, "status", "ok")
        >>> router = create_branch_router("status", {"ok": "continue", "error": "handle_error"})
        >>> router(state)
        'continue'
    """

    def branch_router(state: DialogueState | dict[str, Any]) -> str:
        """
        Route based on input variable value.

        Args:
            state: Current dialogue state

        Returns:
            Target step name from cases mapping

        Raises:
            ValueError: If input variable not found or value not in cases
        """
        # Ensure we have DialogueState (TypedDict)
        if isinstance(state, dict):
            # Convert if plain dict
            if "flow_stack" not in state:
                state = state_from_dict(state)
        # Otherwise it's already a DialogueState (TypedDict is a dict)

        # Get value from slots (where map_outputs stores variables)
        value = get_slot(state, input_var)

        if value is None:
            # Get available slots for error message
            from soni.core.state import get_all_slots

            all_slots = get_all_slots(state)
            logger.warning(
                f"Branch router: input variable '{input_var}' not found in state slots",
                extra={"input_var": input_var, "available_slots": list(all_slots.keys())},
            )
            # Try to find a default case or raise error
            # For now, raise error - could be extended to support default case
            raise ValueError(
                f"Branch router: input variable '{input_var}' not found in state. "
                f"Available slots: {list(all_slots.keys())}"
            )

        # Convert value to string for comparison (cases keys are strings)
        value_str = str(value)

        # Look up target in cases
        if value_str in cases:
            target = cases[value_str]
            logger.debug(
                f"Branch router: '{input_var}' = '{value_str}' -> '{target}'",
                extra={"input_var": input_var, "value": value_str, "target": target},
            )
            return target

        # Value not found in cases
        logger.warning(
            f"Branch router: value '{value_str}' not found in cases for '{input_var}'",
            extra={
                "input_var": input_var,
                "value": value_str,
                "available_cases": list(cases.keys()),
            },
        )
        raise ValueError(
            f"Branch router: value '{value_str}' not found in cases for '{input_var}'. "
            f"Available cases: {list(cases.keys())}"
        )

    return branch_router


def activate_flow_by_intent(
    command: str | None,
    current_flow: str,
    config: Any,
) -> str:
    """
    Activate flow based on intent (command).

    Args:
        command: NLU command/intent
        current_flow: Current flow name
        config: Soni configuration

    Returns:
        New flow name or current flow
    """
    if not command:
        return current_flow

    # Check if command corresponds to a configured flow
    # config is SoniConfig, which has flows attribute (dict)
    if hasattr(config, "flows") and command in config.flows:
        logger.info(f"Activating flow '{command}' based on intent")
        return command

    return current_flow


def should_continue_flow(state: DialogueState) -> Literal["next", "end"]:
    """
    Determine if the flow should continue to the next node or stop.

    This function implements the interactive state machine logic:
    - If the last event indicates we need user input (slot collection or validation error),
      we stop the flow ("end").
    - Otherwise, we continue to the next node ("next").

    Args:
        state: Current dialogue state

    Returns:
        "end" if the flow should stop (wait for user input), "next" otherwise.
    """
    trace = state.get("trace", [])
    if not trace:
        return "next"

    last_event = trace[-1]
    event_type = last_event.get("event")

    # Stop if we just asked for a slot or encountered a validation error
    if event_type in [EVENT_SLOT_COLLECTION, EVENT_VALIDATION_ERROR]:
        return "end"

    return "next"


def route_after_understand(state: DialogueStateType) -> str:
    """
    Route based on NLU result.

    Pattern: Routing Function (synchronous, returns node name)

    Args:
        state: Current dialogue state

    Returns:
        Name of next node to execute
    """
    nlu_result = state.get("nlu_result")

    if not nlu_result:
        return "generate_response"

    message_type = nlu_result.get("message_type")

    # Route based on message type
    match message_type:
        case "slot_value":
            return "validate_slot"
        case "correction":
            return "handle_correction"
        case "modification":
            return "handle_modification"
        case "interruption":
            return "handle_intent_change"
        case "digression":
            return "handle_digression"
        case "clarification":
            return "handle_clarification"
        case "cancellation":
            return "handle_cancellation"
        case "confirmation":
            return "handle_confirmation"
        case "continuation":
            return "continue_flow"
        case _:
            return "generate_response"


def route_after_validate(state: DialogueStateType) -> str:
    """
    Route after slot validation.

    Args:
        state: Current dialogue state

    Returns:
        Next node name
    """
    # Check if all required slots filled
    flow_stack = state.get("flow_stack", [])
    active_flow = flow_stack[-1] if flow_stack else None

    if not active_flow:
        return "generate_response"

    # TODO: Check slot requirements from flow definition
    # For now, simple logic
    if state.get("all_slots_filled"):
        return "execute_action"
    else:
        return "collect_next_slot"
