"""Dialogue state management for Soni Framework.

This module provides TypedDict-based state management for LangGraph compatibility.
All state operations are functional (immutable by convention) to ensure proper
state tracking and checkpointing.
"""

from __future__ import annotations

import copy
import json
import time
from typing import TYPE_CHECKING, Any, cast

from soni.core.errors import ValidationError
from soni.core.types import DialogueState, FlowContext, RuntimeContext
from soni.core.validators import validate_state_consistency, validate_transition

if TYPE_CHECKING:
    from soni.core.config import SoniConfig
    from soni.core.interfaces import IActionHandler, INLUProvider, INormalizer, IScopeManager
else:
    # Import for runtime (mypy needs these at runtime for type checking)
    from soni.core.interfaces import IActionHandler, INLUProvider, INormalizer, IScopeManager


# ============================================================================
# RuntimeContext Helper Functions
# ============================================================================


def create_runtime_context(
    config: SoniConfig,
    scope_manager: IScopeManager,
    normalizer: INormalizer,
    action_handler: IActionHandler,
    du: INLUProvider,
    flow_manager: Any | None = None,
    step_manager: Any | None = None,
) -> RuntimeContext:
    """Create a RuntimeContext with all dependencies.

    Args:
        config: Soni configuration
        scope_manager: Scope manager for action filtering
        normalizer: Slot normalizer for value normalization
        action_handler: Handler for executing actions
        du: NLU provider for dialogue understanding
        flow_manager: Optional flow manager (created if None)
        step_manager: Optional step manager (created if None)

    Returns:
        RuntimeContext TypedDict
    """
    # Import here to avoid circular imports
    if flow_manager is None:
        from soni.flow.manager import FlowManager

        flow_manager = FlowManager(config=config)

    if step_manager is None:
        from soni.flow.step_manager import FlowStepManager

        step_manager = FlowStepManager(config)

    return {
        "config": config,
        "scope_manager": scope_manager,
        "normalizer": normalizer,
        "action_handler": action_handler,
        "du": du,
        "flow_manager": flow_manager,
        "step_manager": step_manager,
    }


def get_slot_config(context: RuntimeContext, slot_name: str) -> Any:
    """Get configuration for a specific slot.

    Args:
        context: Runtime context
        slot_name: Name of the slot

    Returns:
        Slot configuration

    Raises:
        KeyError: If slot not found in config
    """
    config = context["config"]
    return config.slots[slot_name]


def get_action_config(context: RuntimeContext, action_name: str) -> Any:
    """Get configuration for a specific action.

    Args:
        context: Runtime context
        action_name: Name of the action

    Returns:
        Action configuration

    Raises:
        KeyError: If action not found in config
    """
    config = context["config"]
    return config.actions[action_name]


def get_flow_config(context: RuntimeContext, flow_name: str) -> Any:
    """Get configuration for a specific flow.

    Args:
        context: Runtime context
        flow_name: Name of the flow

    Returns:
        Flow configuration

    Raises:
        KeyError: If flow not found in config
    """
    config = context["config"]
    return config.flows[flow_name]


# ============================================================================
# DialogueState Helper Functions (TypedDict-based)
# ============================================================================
# These functions provide a functional API for working with DialogueState
# TypedDict, ensuring immutability and proper state tracking for LangGraph.


def create_empty_state() -> DialogueState:
    """Create an empty DialogueState with defaults.

    Returns:
        DialogueState TypedDict with all default values
    """
    return {
        "user_message": "",
        "last_response": "",
        "messages": [],
        "flow_stack": [],
        "flow_slots": {},
        "conversation_state": "idle",
        "current_step": None,
        "waiting_for_slot": None,
        "current_prompted_slot": None,
        "all_slots_filled": None,
        "nlu_result": None,
        "action_result": None,
        "last_nlu_call": None,
        "digression_depth": 0,
        "last_digression_type": None,
        "turn_count": 0,
        "trace": [],
        "metadata": {},
    }


def create_initial_state(user_message: str) -> DialogueState:
    """Create initial state for new conversation.

    Args:
        user_message: Initial user message

    Returns:
        DialogueState TypedDict initialized for new conversation
    """
    state = create_empty_state()
    state["user_message"] = user_message
    state["conversation_state"] = "understanding"
    state["turn_count"] = 1
    state["trace"] = [
        {
            "turn": 1,
            "user_message": user_message,
            "timestamp": time.time(),
        }
    ]
    return state


def update_state(
    state: DialogueState,
    updates: dict[str, Any],
    validate: bool = True,
) -> None:
    """
    Update dialogue state with validation.

    Args:
        state: Current dialogue state (modified in place)
        updates: Partial updates to apply
        validate: Whether to validate transition (default True)

    Raises:
        ValidationError: If update would create invalid state
    """
    # Validate conversation_state transition if changing
    if validate and "conversation_state" in updates:
        validate_transition(
            state["conversation_state"],
            updates["conversation_state"],
        )

    # Apply updates to state dict
    # Cast to plain dict for dynamic key assignment (safe after validation)
    state_dict = cast(dict[str, Any], state)
    for key, value in updates.items():
        if key in state_dict:
            state_dict[key] = value

    # Validate final state consistency
    if validate:
        validate_state_consistency(state)


def state_to_dict(state: DialogueState) -> dict[str, Any]:
    """
    Serialize DialogueState to JSON-compatible dict.

    Args:
        state: Dialogue state

    Returns:
        JSON-serializable dictionary
    """
    # DialogueState is already a dict (TypedDict), but ensure deep copy
    return copy.deepcopy(dict(state))


def state_from_dict(data: dict[str, Any], allow_partial: bool = False) -> DialogueState:
    """
    Deserialize DialogueState from dict.

    Args:
        data: Dictionary with state data
        allow_partial: If True, fill missing fields with defaults instead of raising error

    Returns:
        DialogueState

    Raises:
        ValidationError: If data is invalid and allow_partial=False
    """
    # If allow_partial, merge with default state
    if allow_partial:
        default_state = create_empty_state()
        # Merge: default first, then data (data takes precedence)
        # Use update to avoid TypedDict literal-required error
        merged: dict[str, Any] = dict(default_state)
        merged.update(data)
        # Cast early for type checking
        merged_state = cast(DialogueState, merged)
        # Validate consistency
        validate_state_consistency(merged_state)
        return merged_state

    # Validate required fields (strict mode)
    required_fields = [
        "user_message",
        "last_response",
        "messages",
        "flow_stack",
        "flow_slots",
        "conversation_state",
        "turn_count",
        "trace",
        "metadata",
    ]

    for required_field in required_fields:
        if required_field not in data:
            raise ValidationError(
                f"Missing required field: {required_field}",
                field=required_field,
            )

    # Cast dict to DialogueState after validation (safe - all required fields present)
    state = cast(DialogueState, data)

    # Validate consistency
    validate_state_consistency(state)

    return state


def state_to_json(state: DialogueState) -> str:
    """Serialize state to JSON string."""
    return json.dumps(state_to_dict(state), indent=2)


def state_from_json(json_str: str) -> DialogueState:
    """Deserialize state from JSON string."""
    data = json.loads(json_str)
    return state_from_dict(data)


# ============================================================================
# Message Operations
# ============================================================================


def add_message(state: DialogueState | dict[str, Any], role: str, content: str) -> None:
    """Add a message to the conversation history (mutates state in place).

    Args:
        state: Current dialogue state (dict or DialogueState TypedDict)
        role: Message role ('user' or 'assistant')
        content: Message content
    """
    if "messages" not in state:
        state["messages"] = []
    state["messages"].append({"role": role, "content": content})


def get_user_messages(state: DialogueState | dict[str, Any]) -> list[str]:
    """Get all user messages from state.

    Args:
        state: Current dialogue state

    Returns:
        List of user message contents
    """
    return [msg["content"] for msg in state["messages"] if msg.get("role") == "user"]


def get_assistant_messages(state: DialogueState | dict[str, Any]) -> list[str]:
    """Get all assistant messages from state.

    Args:
        state: Current dialogue state

    Returns:
        List of assistant message contents
    """
    return [msg["content"] for msg in state["messages"] if msg.get("role") == "assistant"]


# ============================================================================
# Slot Operations
# ============================================================================


def get_slot(state: DialogueState | dict[str, Any], slot_name: str, default: Any = None) -> Any:
    """Get a slot value by name from active flow.

    Args:
        state: Current dialogue state (dict or DialogueState TypedDict)
        slot_name: Name of the slot
        default: Default value if slot not found

    Returns:
        Slot value or default
    """
    # Get active flow from flow_stack
    flow_stack = state.get("flow_stack", [])
    if flow_stack:
        active_flow = flow_stack[-1]
        flow_id = active_flow["flow_id"]
        flow_slots = state.get("flow_slots", {})
        return flow_slots.get(flow_id, {}).get(slot_name, default)
    return default


def set_slot(state: DialogueState | dict[str, Any], slot_name: str, value: Any) -> None:
    """Set a slot value in active flow (mutates state in place).

    Args:
        state: Current dialogue state (dict or DialogueState TypedDict)
        slot_name: Name of the slot
        value: Value to set
    """
    # Get active flow from flow_stack
    flow_stack = state.get("flow_stack", [])
    if flow_stack:
        active_flow = flow_stack[-1]
        flow_id = active_flow["flow_id"]
        flow_slots = state.get("flow_slots", {})
        if flow_id not in flow_slots:
            flow_slots[flow_id] = {}
        flow_slots[flow_id][slot_name] = value


def has_slot(state: DialogueState | dict[str, Any], slot_name: str) -> bool:
    """Check if a slot is filled in active flow.

    Args:
        state: Current dialogue state (dict or DialogueState TypedDict)
        slot_name: Name of the slot

    Returns:
        True if slot exists and is not None
    """
    value = get_slot(state, slot_name)
    return value is not None


def clear_slots(state: DialogueState | dict[str, Any]) -> None:
    """Clear all slots in active flow (mutates state in place).

    Args:
        state: Current dialogue state (dict or DialogueState TypedDict)
    """
    # Clear slots for active flow
    flow_stack = state.get("flow_stack", [])
    if flow_stack:
        active_flow = flow_stack[-1]
        flow_id = active_flow["flow_id"]
        flow_slots = state.get("flow_slots", {})
        if flow_id in flow_slots:
            flow_slots[flow_id].clear()


# ============================================================================
# Turn and Trace Operations
# ============================================================================


def increment_turn(state: DialogueState | dict[str, Any]) -> None:
    """Increment turn counter (mutates state in place).

    Args:
        state: Current dialogue state (dict or DialogueState TypedDict)
    """
    state["turn_count"] += 1


def add_trace(state: DialogueState | dict[str, Any], event: str, data: dict[str, Any]) -> None:
    """Add a trace event for debugging (mutates state in place).

    Args:
        state: Current dialogue state (dict or DialogueState TypedDict)
        event: Event name
        data: Event data
    """
    state["trace"].append({"event": event, "data": data})


# ============================================================================
# Flow Operations
# ============================================================================


def get_current_flow(state: DialogueState | dict[str, Any]) -> str:
    """Get current active flow name.

    Args:
        state: Current dialogue state (dict or DialogueState TypedDict)

    Returns:
        Active flow name or "none" if no active flow
    """
    flow_stack = state.get("flow_stack", [])
    if flow_stack:
        return flow_stack[-1]["flow_name"]
    return "none"


def get_current_flow_context(state: DialogueState | dict[str, Any]) -> FlowContext | None:
    """Get current active flow context.

    Args:
        state: Current dialogue state (dict or DialogueState TypedDict)

    Returns:
        Active flow context or None if no active flow
    """
    flow_stack = state.get("flow_stack", [])
    if flow_stack:
        return flow_stack[-1]
    return None


def push_flow(
    state: DialogueState | dict[str, Any],
    flow_name: str,
    flow_id: str | None = None,
    context: str | None = None,
) -> None:
    """Push a new flow onto the flow stack (mutates state in place).

    Args:
        state: Current dialogue state (dict or DialogueState TypedDict)
        flow_name: Name of the flow to activate
        flow_id: Optional unique ID for this flow instance (auto-generated if None)
        context: Optional context string for the flow
    """
    if flow_id is None:
        flow_id = f"{flow_name}_{int(time.time() * 1000)}"

    flow_context: FlowContext = {
        "flow_id": flow_id,
        "flow_name": flow_name,
        "flow_state": "active",
        "current_step": None,
        "outputs": {},
        "started_at": time.time(),
        "paused_at": None,
        "completed_at": None,
        "context": context,
    }

    flow_stack = state.get("flow_stack", [])
    flow_stack.append(flow_context)
    state["flow_stack"] = flow_stack

    # Initialize slots for this flow
    flow_slots = state.get("flow_slots", {})
    if flow_id not in flow_slots:
        flow_slots[flow_id] = {}
    state["flow_slots"] = flow_slots


def pop_flow(state: DialogueState | dict[str, Any]) -> FlowContext | None:
    """Pop the current flow from the flow stack (mutates state in place).

    Args:
        state: Current dialogue state (dict or DialogueState TypedDict)

    Returns:
        Popped flow context or None if stack was empty
    """
    flow_stack = state.get("flow_stack", [])
    if flow_stack:
        popped = flow_stack.pop()
        state["flow_stack"] = flow_stack
        return popped
    return None


def get_all_slots(state: DialogueState | dict[str, Any]) -> dict[str, Any]:
    """Get all slots from active flow as a flat dictionary.

    Args:
        state: Current dialogue state (dict or DialogueState TypedDict)

    Returns:
        Dictionary of all slots in active flow (empty dict if no active flow)
    """
    flow_stack = state.get("flow_stack", [])
    if flow_stack:
        active_flow = flow_stack[-1]
        flow_id = active_flow["flow_id"]
        flow_slots = state.get("flow_slots", {})
        return flow_slots.get(flow_id, {}).copy()
    return {}


# ============================================================================
# State Access Helpers (consistent defaults, reduces coupling)
# ============================================================================


def get_nlu_result(state: DialogueState | dict[str, Any]) -> dict[str, Any]:
    """Get NLU result from state with consistent defaults.

    Args:
        state: Current dialogue state

    Returns:
        NLU result dictionary, or empty dict if not set
    """
    nlu_result = state.get("nlu_result")
    return nlu_result if nlu_result is not None else {}


def get_metadata(state: DialogueState | dict[str, Any]) -> dict[str, Any]:
    """Get metadata from state with consistent defaults.

    Args:
        state: Current dialogue state

    Returns:
        Metadata dictionary, or empty dict if not set
    """
    return state.get("metadata", {})


def get_conversation_state(
    state: DialogueState | dict[str, Any],
    default: str = "idle",
) -> str:
    """Get conversation state with consistent defaults.

    Args:
        state: Current dialogue state
        default: Default conversation state if not set (default: "idle")

    Returns:
        Conversation state string
    """
    return state.get("conversation_state", default)


def get_flow_stack(state: DialogueState | dict[str, Any]) -> list[Any]:
    """Get flow stack from state with consistent defaults.

    Args:
        state: Current dialogue state

    Returns:
        Flow stack list, or empty list if not set
    """
    return state.get("flow_stack", [])


def get_user_message(state: DialogueState | dict[str, Any]) -> str:
    """Get user message from state.

    Args:
        state: Current dialogue state

    Returns:
        User message string, or empty string if not set
    """
    return state.get("user_message", "")


def get_last_response(state: DialogueState | dict[str, Any]) -> str:
    """Get last response from state.

    Args:
        state: Current dialogue state

    Returns:
        Last response string, or empty string if not set
    """
    return state.get("last_response", "")


def get_action_result(state: DialogueState | dict[str, Any]) -> Any:
    """Get action result from state.

    Args:
        state: Current dialogue state

    Returns:
        Action result (can be any type), or None if not set
    """
    return state.get("action_result")


def set_all_slots(state: DialogueState | dict[str, Any], slots: dict[str, Any]) -> None:
    """Set all slots for active flow (mutates state in place).

    Args:
        state: Current dialogue state (dict or DialogueState TypedDict)
        slots: Dictionary of slot values to set
    """
    flow_stack = state.get("flow_stack", [])
    if flow_stack:
        active_flow = flow_stack[-1]
        flow_id = active_flow["flow_id"]
        flow_slots = state.get("flow_slots", {})
        if flow_id not in flow_slots:
            flow_slots[flow_id] = {}
        flow_slots[flow_id].update(slots)
        state["flow_slots"] = flow_slots


def get_current_step_config(
    state: DialogueState | dict[str, Any],
    context: RuntimeContext,
) -> Any:  # StepConfig
    """Get configuration for current step.

    Args:
        state: Current dialogue state
        context: Runtime context with dependencies

    Returns:
        StepConfig for current step, or None if no current step
    """
    step_manager = context["step_manager"]
    return step_manager.get_current_step_config(state, context)


def get_next_step_config(
    state: DialogueState | dict[str, Any],
    context: RuntimeContext,
) -> Any:  # StepConfig
    """Get configuration for next step in sequence.

    Args:
        state: Current dialogue state
        context: Runtime context with dependencies

    Returns:
        StepConfig for next step, or None if no next step (flow complete)
    """
    step_manager = context["step_manager"]
    return step_manager.get_next_step_config(state, context)


def update_current_step(
    state: DialogueState | dict[str, Any],
    step_name: str | None,
) -> None:
    """Update current_step in FlowContext (mutates state).

    Args:
        state: Current dialogue state (dict or DialogueState TypedDict)
        step_name: Name of step to set as current, or None to clear
    """
    flow_stack = state.get("flow_stack", [])
    if flow_stack:
        active_ctx = flow_stack[-1]
        active_ctx["current_step"] = step_name
