"""Routing logic for dialogue flows"""

import logging
from collections.abc import Callable
from typing import Any, Literal

from soni.core.events import EVENT_SLOT_COLLECTION, EVENT_VALIDATION_ERROR
from soni.core.state import DialogueState

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
    if isinstance(state, dict):
        state = DialogueState.from_dict(state)

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
    if isinstance(state, dict):
        state = DialogueState.from_dict(state)

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
        >>> router = create_branch_router("status", {"ok": "continue", "error": "handle_error"})
        >>> state = DialogueState(slots={"status": "ok"})
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
        # Convert dict to DialogueState if needed
        if isinstance(state, dict):
            state = DialogueState.from_dict(state)

        # Get value from slots (where map_outputs stores variables)
        value = state.get_slot(input_var)

        if value is None:
            logger.warning(
                f"Branch router: input variable '{input_var}' not found in state slots",
                extra={"input_var": input_var, "available_slots": list(state.slots.keys())},
            )
            # Try to find a default case or raise error
            # For now, raise error - could be extended to support default case
            raise ValueError(
                f"Branch router: input variable '{input_var}' not found in state. "
                f"Available slots: {list(state.slots.keys())}"
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
    if not state.trace:
        return "next"

    last_event = state.trace[-1]
    event_type = last_event.get("event")

    # Stop if we just asked for a slot or encountered a validation error
    if event_type in [EVENT_SLOT_COLLECTION, EVENT_VALIDATION_ERROR]:
        return "end"

    return "next"
