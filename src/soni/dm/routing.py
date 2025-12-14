"""Routing logic for dialogue flows"""

import logging
from collections.abc import Callable
from functools import wraps
from typing import Any, Literal, cast

from pydantic import BaseModel, Field, ValidationError

from soni.core.constants import ConversationState, NodeName
from soni.core.events import EVENT_SLOT_COLLECTION, EVENT_VALIDATION_ERROR
from soni.core.state import DialogueState, get_slot, state_from_dict
from soni.core.types import DialogueState as DialogueStateType

logger = logging.getLogger(__name__)


def log_routing_decision(func: Callable) -> Callable:
    """Decorator for consistent logging of routing decisions (DM-004).

    Logs entry and result of routing functions with structured data.

    Usage:
        @log_routing_decision
        def my_route_handler(state, nlu_result):
            return NodeName.VALIDATE_SLOT
    """

    @wraps(func)
    def wrapper(state: DialogueStateType, *args, **kwargs) -> str:
        func_name = func.__name__
        conv_state = state.get("conversation_state")

        logger.debug(
            f"[ROUTE] {func_name} entry",
            extra={
                "router": func_name,
                "conversation_state": conv_state,
            },
        )

        result = func(state, *args, **kwargs)

        logger.info(
            f"[ROUTE] {func_name} -> {result}",
            extra={
                "router": func_name,
                "conversation_state": conv_state,
                "next_node": result,
            },
        )

        return cast(str, result)

    return wrapper


# =============================================================================
# NLU Result Validation (DM-005)
# Pydantic schema validation at routing boundary for type safety
# =============================================================================


class ValidatedNLUResult(BaseModel):
    """Validated NLU result with type-safe fields.

    Used at the routing boundary to ensure NLU results have valid structure
    before processing. Provides clear error messages for malformed results.
    """

    message_type: str = Field(description="Classification of user message type")
    command: str | None = Field(default=None, description="Flow/intent command if applicable")
    slots: list[dict[str, Any]] = Field(default_factory=list, description="Extracted slot values")
    confidence: float = Field(default=0.0, ge=0.0, le=1.0, description="NLU confidence score")
    confirmation_value: bool | None = Field(
        default=None, description="Confirmation response (True/False/None)"
    )


class NLUResultValidationError(Exception):
    """Error raised when NLU result fails validation.

    Contains the original data for debugging.
    """

    def __init__(self, validation_error: ValidationError, original_data: dict[str, Any]):
        self.validation_error = validation_error
        self.original_data = original_data
        super().__init__(
            f"NLU result validation failed: {validation_error}. Original data: {original_data}"
        )


def validate_nlu_result(nlu_result: dict[str, Any] | None) -> ValidatedNLUResult | None:
    """Validate NLU result at routing boundary.

    Args:
        nlu_result: Raw NLU result dict or None

    Returns:
        ValidatedNLUResult if valid, None if input is None

    Raises:
        NLUResultValidationError: If validation fails
    """
    if nlu_result is None:
        return None

    try:
        return cast(ValidatedNLUResult, ValidatedNLUResult.model_validate(nlu_result))
    except ValidationError as e:
        logger.error(
            f"NLU result validation failed: {e}",
            extra={"nlu_result": nlu_result},
        )
        raise NLUResultValidationError(e, nlu_result) from e


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

    # 2. Handle underscore/hyphen/space variations
    # Normalize: spaces -> underscores, hyphens -> underscores, then lowercase
    normalized_command = command.replace(" ", "_").replace("-", "_").lower()
    for flow_name in config.flows:
        if normalized_command == flow_name.lower():
            logger.info(
                f"Activating flow '{flow_name}' based on intent (normalized from '{command}')"
            )
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


def _route_by_conversation_state(
    state: DialogueStateType,
    router_name: str,
    *,
    handle_completed: bool = False,
    verbose_logging: bool = False,
) -> str:
    """
    Common routing logic based on conversation_state.

    This helper consolidates the shared routing pattern used by:
    - route_after_validate
    - route_after_correction
    - route_after_modification

    Args:
        state: Current dialogue state
        router_name: Name of the calling router (for logging)
        handle_completed: If True, treat "completed" state as generate_response
        verbose_logging: If True, log detailed state information

    Returns:
        Next node name based on conversation_state
    """
    conv_state = state.get("conversation_state")

    if verbose_logging:
        logger.info("=" * 80)
        logger.info(f"ROUTING after {router_name}:")
        logger.info(f"  conversation_state: {conv_state}")
        logger.info(f"  last_response: '{state.get('last_response')}'")
        logger.info(f"  user_message: '{state.get('user_message')}'")
        logger.info(f"  waiting_for_slot: '{state.get('waiting_for_slot')}'")
        logger.info(f"  current_prompted_slot: '{state.get('current_prompted_slot')}'")
        logger.info("=" * 80)
    else:
        logger.info(
            f"{router_name}: conversation_state={conv_state}",
            extra={"conversation_state": conv_state},
        )

    # Common routing based on conversation_state
    if conv_state == ConversationState.READY_FOR_ACTION:
        return NodeName.EXECUTE_ACTION
    elif conv_state == ConversationState.READY_FOR_CONFIRMATION:
        return NodeName.CONFIRM_ACTION
    elif conv_state == ConversationState.WAITING_FOR_SLOT:
        return NodeName.COLLECT_NEXT_SLOT
    elif handle_completed and conv_state == ConversationState.COMPLETED:
        return NodeName.GENERATE_RESPONSE
    else:
        if verbose_logging:
            logger.warning(
                f"Unexpected conversation_state '{conv_state}' in {router_name}, "
                f"falling back to generate_response. State keys: {list(state.keys())}",
                extra={
                    "conversation_state": conv_state,
                    "state_keys": list(state.keys()),
                    "has_nlu_result": "nlu_result" in state,
                },
            )
        return NodeName.GENERATE_RESPONSE


# =============================================================================
# Route Handlers for dispatch pattern (DM-001)
# Each handler processes a specific message_type from NLU
# =============================================================================


def _normalize_message_type(message_type: Any) -> str | None:
    """Normalize message_type to lowercase string.

    Args:
        message_type: Raw message type (string, enum, or None)

    Returns:
        Lowercase string or None
    """
    if message_type is None:
        return None
    # If it's an enum, get its value (string)
    if hasattr(message_type, "value"):
        message_type = message_type.value
    return str(message_type).lower()


def _redirect_if_confirming(state: DialogueStateType, message_type: str) -> str | None:
    """Guard: redirect to handle_confirmation if in confirming state.

    This consolidates the duplicated check across slot_value, correction,
    and modification handlers (DRY principle - DM-003).

    Args:
        state: Current dialogue state
        message_type: The message type being processed (for logging)

    Returns:
        NodeName.HANDLE_CONFIRMATION if in confirming state, None otherwise
    """
    conv_state = state.get("conversation_state")

    if conv_state == ConversationState.CONFIRMING:
        logger.info(
            f"Guard: {message_type} detected during confirming state, "
            f"redirecting to handle_confirmation"
        )
        return NodeName.HANDLE_CONFIRMATION

    return None


def _route_slot_value(state: DialogueStateType, nlu_result: dict[str, Any]) -> str:
    """Route slot_value message type.

    Handles special cases:
    - If confirming: treat as confirmation
    - If understanding after denial: treat as modification
    - If no active flow but has command: start flow first
    """
    # Guard: redirect if in confirming state
    if redirect := _redirect_if_confirming(state, "slot_value"):
        return redirect

    conv_state = state.get("conversation_state")

    # Special case: In understanding state after denial, treat as modification
    if conv_state == ConversationState.UNDERSTANDING:
        flow_stack = state.get("flow_stack", [])
        if flow_stack:
            from soni.core.state import get_all_slots

            existing_slots = get_all_slots(state)
            slots = nlu_result.get("slots", [])
            if slots:
                slot = slots[0]
                slot_name = (
                    slot.get("name") if isinstance(slot, dict) else getattr(slot, "name", None)
                )
                if slot_name and slot_name in existing_slots:
                    logger.info(
                        f"slot_value detected but slot '{slot_name}' already exists "
                        f"and conversation_state=understanding (after denial), "
                        f"treating as modification"
                    )
                    return NodeName.HANDLE_MODIFICATION

    # Check if flow needs to be started first
    flow_stack = state.get("flow_stack", [])
    has_active_flow = bool(flow_stack)
    command = nlu_result.get("command")

    if not has_active_flow and command:
        logger.info(
            f"slot_value message with command '{command}' but no active flow, starting flow first"
        )
        return NodeName.HANDLE_INTENT_CHANGE

    return NodeName.VALIDATE_SLOT


def _route_correction(state: DialogueStateType, nlu_result: dict[str, Any]) -> str:
    """Route correction message type."""
    # Guard: redirect if in confirming state
    if redirect := _redirect_if_confirming(state, "correction"):
        return redirect

    flow_stack = state.get("flow_stack", [])
    has_active_flow = bool(flow_stack)
    command = nlu_result.get("command")

    logger.info(
        f"route_after_understand: CORRECTION detected, has_active_flow={has_active_flow}, "
        f"command={command}, routing to handle_correction"
    )

    if not has_active_flow and command:
        logger.info(
            f"correction message with command '{command}' but no active flow, starting flow first"
        )
        return NodeName.HANDLE_INTENT_CHANGE

    return NodeName.HANDLE_CORRECTION


def _route_modification(state: DialogueStateType, nlu_result: dict[str, Any]) -> str:
    """Route modification message type."""
    # Guard: redirect if in confirming state
    if redirect := _redirect_if_confirming(state, "modification"):
        return redirect

    flow_stack = state.get("flow_stack", [])
    has_active_flow = bool(flow_stack)
    command = nlu_result.get("command")

    if not has_active_flow and command:
        logger.info(
            f"modification message with command '{command}' but no active flow, starting flow first"
        )
        return NodeName.HANDLE_INTENT_CHANGE

    return NodeName.HANDLE_MODIFICATION


def _route_intent_change(state: DialogueStateType, nlu_result: dict[str, Any]) -> str:
    """Route interruption/intent_change message type."""
    return NodeName.HANDLE_INTENT_CHANGE


def _route_clarification(state: DialogueStateType, nlu_result: dict[str, Any]) -> str:
    """Route clarification message type.

    Special case: If the user asks something that NLU classifies as clarification
    but the command matches a DIFFERENT available flow, treat it as an interruption.
    This handles cases like "how much do I have?" during transfer being classified
    as clarification but actually wanting to check_balance.
    """
    command = nlu_result.get("command")
    flow_stack = state.get("flow_stack", [])

    if command and flow_stack:
        # Get current flow name
        active_ctx = flow_stack[-1] if flow_stack else None
        current_flow = active_ctx.get("flow_name") if active_ctx else None

        # If command is a different flow, treat as interruption
        if current_flow and command != current_flow:
            logger.info(
                f"Clarification rerouted to intent_change: command '{command}' != current_flow '{current_flow}'"
            )
            return NodeName.HANDLE_INTENT_CHANGE

    return NodeName.HANDLE_CLARIFICATION


def _route_digression(state: DialogueStateType, nlu_result: dict[str, Any]) -> str:
    """Route digression/question message type.

    Special case: If the NLU classifies as digression but the command
    matches a DIFFERENT available flow, treat it as an interruption.
    This handles semantic ambiguity where questions like "how much do I have?"
    are misclassified as digression instead of check_balance interruption.
    """
    command = nlu_result.get("command")
    flow_stack = state.get("flow_stack", [])

    if command and flow_stack:
        # Get current flow name
        active_ctx = flow_stack[-1] if flow_stack else None
        current_flow = active_ctx.get("flow_name") if active_ctx else None

        # If command is a different flow, treat as interruption
        if current_flow and command != current_flow:
            logger.info(
                f"Digression rerouted to intent_change: command '{command}' != current_flow '{current_flow}'"
            )
            return NodeName.HANDLE_INTENT_CHANGE

    return NodeName.HANDLE_DIGRESSION


def _route_cancellation(state: DialogueStateType, nlu_result: dict[str, Any]) -> str:
    """Route cancellation message type."""
    return NodeName.HANDLE_CANCELLATION


def _route_confirmation(state: DialogueStateType, nlu_result: dict[str, Any]) -> str:
    """Route confirmation message type."""
    conv_state = state.get("conversation_state")

    if (
        conv_state == ConversationState.CONFIRMING
        or conv_state == ConversationState.READY_FOR_CONFIRMATION
    ):
        return NodeName.HANDLE_CONFIRMATION

    # Not in confirmation state - treat as continuation or digression
    logger.warning(
        f"NLU detected confirmation but conversation_state={conv_state}, treating as continuation"
    )
    flow_stack = state.get("flow_stack", [])
    has_active_flow = bool(flow_stack)

    if has_active_flow:
        return NodeName.COLLECT_NEXT_SLOT
    return NodeName.GENERATE_RESPONSE


def _route_continuation(state: DialogueStateType, nlu_result: dict[str, Any]) -> str:
    """Route continuation message type."""
    flow_stack = state.get("flow_stack", [])
    has_active_flow = bool(flow_stack)
    command = nlu_result.get("command")

    if has_active_flow:
        return NodeName.COLLECT_NEXT_SLOT
    elif command:
        logger.info(
            f"Continuation with no active flow and command '{command}', treating as intent_change"
        )
        return NodeName.HANDLE_INTENT_CHANGE
    return NodeName.GENERATE_RESPONSE


def _route_fallback(state: DialogueStateType, nlu_result: dict[str, Any]) -> str:
    """Fallback handler for unknown message types."""
    message_type = nlu_result.get("message_type") if nlu_result else None
    logger.warning(
        f"Unknown message_type '{message_type}' in route_after_understand, "
        f"falling back to generate_response.",
        extra={
            "message_type": message_type,
            "command": nlu_result.get("command") if nlu_result else None,
        },
    )
    return NodeName.GENERATE_RESPONSE


# Type alias for route handlers
RouteHandler = Callable[[DialogueStateType, dict[str, Any]], str]

# Dispatch dictionary for message types -> handlers
ROUTE_HANDLERS: dict[str, RouteHandler] = {
    "slot_value": _route_slot_value,
    "correction": _route_correction,
    "modification": _route_modification,
    "interruption": _route_intent_change,
    "intent_change": _route_intent_change,
    "clarification": _route_clarification,
    "digression": _route_digression,
    "question": _route_digression,
    "cancellation": _route_cancellation,
    "confirmation": _route_confirmation,
    "continuation": _route_continuation,
}


def route_after_understand(state: DialogueStateType) -> str:
    """Route based on NLU result using dispatch pattern.

    Pattern: Routing Function (synchronous, returns node name)

    Args:
        state: Current dialogue state

    Returns:
        Name of next node to execute (from NodeName enum)
    """
    nlu_result = state.get("nlu_result")

    if not nlu_result:
        return NodeName.GENERATE_RESPONSE

    # Normalize message type
    message_type = _normalize_message_type(nlu_result.get("message_type"))

    # Log routing decision
    slots = nlu_result.get("slots", [])

    logger.info(
        f"route_after_understand: message_type={message_type}, command={nlu_result.get('command')}, "
        f"slots_count={len(slots)}",
        extra={
            "message_type": message_type,
            "command": nlu_result.get("command"),
            "slots": [s["name"] for s in slots] if slots else [],
            "confidence": nlu_result.get("confidence"),
        },
    )

    # Dispatch to appropriate handler
    if message_type:
        handler = ROUTE_HANDLERS.get(message_type, _route_fallback)
    else:
        handler = _route_fallback
    return handler(state, nlu_result)


def route_after_correction(state: DialogueStateType) -> str:
    """Route after correction handling based on conversation_state.

    Delegates to _route_by_conversation_state helper (DRY).

    Args:
        state: Current dialogue state

    Returns:
        Next node name
    """
    return _route_by_conversation_state(state, "route_after_correction")


def route_after_modification(state: DialogueStateType) -> str:
    """Route after modification handling based on conversation_state.

    Delegates to _route_by_conversation_state helper (DRY).

    Args:
        state: Current dialogue state

    Returns:
        Next node name
    """
    return _route_by_conversation_state(state, "route_after_modification")


def route_after_validate(state: DialogueStateType) -> str:
    """Route after slot validation based on conversation_state.

    Delegates to _route_by_conversation_state helper with verbose logging (DRY).

    Args:
        state: Current dialogue state

    Returns:
        Next node name
    """
    return _route_by_conversation_state(
        state,
        "validate_slot",
        handle_completed=True,
        verbose_logging=True,
    )


def route_after_collect_next_slot(state: DialogueStateType) -> str:
    """Route after collect_next_slot based on conversation_state.

    When collect_next_slot advances to the next step (because all slots are filled),
    it sets conversation_state based on the next step type. This routing function
    routes to the appropriate node based on that state, avoiding the infinite loop
    of going to understand when there's no user message.

    Args:
        state: Current dialogue state

    Returns:
        Next node name
    """
    conv_state = state.get("conversation_state")

    logger.info("=" * 80)
    logger.info("ROUTING after collect_next_slot:")
    logger.info(f"  conversation_state: {conv_state}")
    logger.info(f"  last_response: '{state.get('last_response')}'")
    logger.info(f"  user_message: '{state.get('user_message')}'")
    logger.info(f"  waiting_for_slot: '{state.get('waiting_for_slot')}'")
    logger.info(f"  current_prompted_slot: '{state.get('current_prompted_slot')}'")
    logger.info("=" * 80)

    # Route based on conversation_state set by advance_to_next_step
    if conv_state == ConversationState.READY_FOR_ACTION:
        return NodeName.EXECUTE_ACTION
    elif conv_state == ConversationState.READY_FOR_CONFIRMATION:
        return NodeName.CONFIRM_ACTION
    elif conv_state == ConversationState.WAITING_FOR_SLOT:
        # Still waiting for a slot - check if we have a user message
        # If we have a user message, go to understand to process it
        # If not, we're in an interrupt state - don't go to understand (would create loop)
        user_message = state.get("user_message", "")
        if user_message and user_message.strip():
            return NodeName.UNDERSTAND
        else:
            # No user message - we're in an interrupt state, generate response
            logger.warning(
                "collect_next_slot: waiting_for_slot but no user_message, "
                "generating response to avoid loop"
            )
            return NodeName.GENERATE_RESPONSE
    elif conv_state == ConversationState.COMPLETED:
        return NodeName.GENERATE_RESPONSE
    elif conv_state == ConversationState.GENERATING_RESPONSE:
        return NodeName.GENERATE_RESPONSE
    else:
        # Default: if we have a user message, go to understand
        # Otherwise, something went wrong
        user_message = state.get("user_message", "")
        if user_message and user_message.strip():
            return NodeName.UNDERSTAND
        else:
            # No user message and unexpected state - generate response
            logger.warning(
                f"Unexpected conversation_state '{conv_state}' in route_after_collect_next_slot, "
                f"no user message, falling back to generate_response"
            )
            return NodeName.GENERATE_RESPONSE


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
    if conv_state == ConversationState.READY_FOR_ACTION:
        # Another action to execute
        logger.info("Routing to execute_action (another action)")
        return NodeName.EXECUTE_ACTION
    elif conv_state == ConversationState.READY_FOR_CONFIRMATION:
        # Next step is a confirmation - display confirmation message
        logger.info("Routing to confirm_action (ready for confirmation)")
        return NodeName.CONFIRM_ACTION
    elif conv_state == ConversationState.COMPLETED:
        # Flow complete, generate final response
        logger.info("Routing to generate_response (flow completed)")
        return NodeName.GENERATE_RESPONSE
    elif conv_state == ConversationState.GENERATING_RESPONSE:
        # Next step is a "say" step - generate response
        logger.info("Routing to generate_response (say step)")
        return NodeName.GENERATE_RESPONSE
    elif conv_state == ConversationState.WAITING_FOR_SLOT:
        # Unexpected: action revealed missing slots
        # This shouldn't happen in current implementation but handle gracefully
        logger.warning("Routing to generate_response (unexpected waiting_for_slot)")
        return NodeName.GENERATE_RESPONSE
    else:
        # Default: flow complete
        logger.info(f"Routing to generate_response (default, state={conv_state})")
        return NodeName.GENERATE_RESPONSE


def route_after_confirmation(state: DialogueStateType) -> str:
    """Route after handling confirmation response.

    Args:
        state: Current dialogue state

    Returns:
        Next node name
    """
    conv_state = state.get("conversation_state")

    # After handling confirmation
    if conv_state == ConversationState.READY_FOR_ACTION:
        # User confirmed, proceed to action
        return NodeName.EXECUTE_ACTION
    elif conv_state == ConversationState.CONFIRMING:
        # Confirmation unclear - show message and wait for next user input
        # Go to generate_response to display the "I didn't understand" message
        # This ends the turn and waits for the next user message (avoids infinite loop)
        return NodeName.GENERATE_RESPONSE
    elif conv_state == ConversationState.ERROR:
        # Max retries exceeded or other error - show error message
        return NodeName.GENERATE_RESPONSE
    elif conv_state == ConversationState.UNDERSTANDING:
        # User denied or wants to modify
        # Go to generate_response to show "What would you like to change?" and END
        # This prevents re-processing the same message through understand
        return NodeName.GENERATE_RESPONSE
    else:
        # Unexpected state - go to generate_response as fallback
        logger.warning(
            f"Unexpected conversation_state={conv_state} after confirmation, routing to generate_response"
        )
        return NodeName.GENERATE_RESPONSE
