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

    Handles multiple command patterns:
    - Exact match: "book_flight" -> activates "book_flight"
    - Start prefix: "start_book_flight" -> activates "book_flight"
    - Underscore variations: "book-flight" -> activates "book_flight"

    Args:
        command: NLU command/intent
        current_flow: Current flow name
        config: Soni configuration

    Returns:
        New flow name or current flow
    """
    if not command:
        return current_flow

    if not hasattr(config, "flows"):
        return current_flow

    # 1. Direct match (design expectation)
    if command in config.flows:
        logger.info(f"Activating flow '{command}' based on intent (exact match)")
        return command

    # 2. Handle 'start_<flow>' pattern (DEPRECATED - legacy code)
    # NOTE: This pattern should no longer be generated after removing start_ prefix from scope.py
    # Keeping temporarily with warning to catch any remaining sources
    if command.startswith("start_"):
        flow_name = command[6:]  # Remove 'start_' prefix
        if flow_name in config.flows:
            logger.warning(
                f"Received legacy 'start_{flow_name}' command - this pattern is deprecated. "
                f"NLU should receive flow names directly. Available flows: {list(config.flows.keys())}"
            )
            return flow_name

    # 3. Handle underscore/hyphen variations
    normalized_command = command.replace("-", "_").lower()
    for flow_name in config.flows:
        if normalized_command == flow_name.lower():
            logger.info(f"Activating flow '{flow_name}' based on intent (normalized)")
            return str(flow_name)

    return str(current_flow)


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

    Note:
        Only returns values that are in the builder.py edge map:
        - validate_slot
        - handle_digression
        - handle_intent_change
        - handle_confirmation
        - collect_next_slot
        - generate_response
    """
    nlu_result = state.get("nlu_result")

    if not nlu_result:
        return "generate_response"

    message_type = nlu_result.get("message_type")

    # Normalize message_type - it can be a string or an enum (MessageType)
    if message_type is not None:
        # If it's an enum, get its value (string)
        if hasattr(message_type, "value"):
            message_type = message_type.value
        # Convert to lowercase for consistent matching
        message_type = str(message_type).lower()

    slots = nlu_result.get("slots", [])
    logger.info(
        f"route_after_understand: message_type={message_type}, command={nlu_result.get('command')}, "
        f"slots_count={len(slots)}",
        extra={
            "message_type": message_type,
            "command": nlu_result.get("command"),
            "slots": [
                s["name"] for s in slots
            ],  # Slots are always dicts after model_dump(mode='json')
            "confidence": nlu_result.get("confidence"),
        },
    )

    # Route based on message type
    # Map to nodes that exist in builder.py edge map
    match message_type:
        case "slot_value":
            return "validate_slot"
        case "correction" | "modification":
            # Corrections and modifications are handled like slot values
            return "validate_slot"
        case "interruption" | "intent_change":
            return "handle_intent_change"
        case "digression" | "question":
            return "handle_digression"
        case "clarification":
            # Clarifications need more info, back to generate_response
            return "generate_response"
        case "cancellation":
            # Cancellation handled by generate_response for now
            return "generate_response"
        case "confirmation":
            return "handle_confirmation"
        case "continuation":
            # Continue the flow - collect next slot
            return "collect_next_slot"
        case _:
            logger.warning(
                f"Unknown message_type '{message_type}' in route_after_understand, "
                f"falling back to generate_response. NLU result: {nlu_result}",
                extra={
                    "message_type": message_type,
                    "command": nlu_result.get("command"),
                    "nlu_result_keys": list(nlu_result.keys())
                    if isinstance(nlu_result, dict)
                    else [],
                },
            )
            return "generate_response"


def route_after_validate(state: DialogueStateType) -> str:
    """Route after slot validation based on conversation_state.

    Args:
        state: Current dialogue state

    Returns:
        Next node name
    """
    conv_state = state.get("conversation_state")

    logger.info(
        f"route_after_validate: conversation_state={conv_state}",
        extra={
            "conversation_state": conv_state,
            "has_nlu_result": "nlu_result" in state,
            "has_flow_slots": bool(state.get("flow_slots")),
        },
    )

    # Route based on conversation_state as specified in design
    if conv_state == "ready_for_action":
        return "execute_action"
    elif conv_state == "ready_for_confirmation":
        return "confirm_action"
    elif conv_state == "waiting_for_slot":
        return "collect_next_slot"
    elif conv_state == "completed":
        return "generate_response"
    else:
        # Default fallback
        return "generate_response"


def route_after_action(state: DialogueStateType) -> str:
    """Route after action execution based on conversation_state.

    Args:
        state: Current dialogue state

    Returns:
        Next node name
    """
    conv_state = state.get("conversation_state")

    logger.info(
        f"route_after_action: conversation_state={conv_state}",
        extra={"conversation_state": conv_state},
    )

    # After executing an action, check what's next
    if conv_state == "ready_for_action":
        # Another action to execute
        logger.info("Routing to execute_action (another action)")
        return "execute_action"
    elif conv_state == "completed":
        # Flow complete, generate final response
        logger.info("Routing to generate_response (flow completed)")
        return "generate_response"
    elif conv_state == "generating_response":
        # Next step is a "say" step - generate response
        logger.info("Routing to generate_response (say step)")
        return "generate_response"
    elif conv_state == "waiting_for_slot":
        # Unexpected: action revealed missing slots
        # This shouldn't happen in current implementation but handle gracefully
        logger.warning("Routing to generate_response (unexpected waiting_for_slot)")
        return "generate_response"
    else:
        # Default: flow complete
        logger.info(f"Routing to generate_response (default, state={conv_state})")
        return "generate_response"


def route_after_confirmation(state: DialogueStateType) -> str:
    """Route after handling confirmation response.

    Args:
        state: Current dialogue state

    Returns:
        Next node name
    """
    conv_state = state.get("conversation_state")

    # After handling confirmation
    if conv_state == "ready_for_action":
        # User confirmed, proceed to action
        return "execute_action"
    elif conv_state == "confirming":
        # Confirmation unclear, ask again (shouldn't happen but handle gracefully)
        return "understand"
    else:
        # User denied or wants to modify, go back to understand
        return "understand"
