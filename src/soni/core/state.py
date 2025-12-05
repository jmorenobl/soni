"""Dialogue state management for Soni Framework."""

from __future__ import annotations

import copy
import json
import time
from dataclasses import asdict, dataclass, field
from typing import TYPE_CHECKING, Any

from soni.core.errors import ValidationError
from soni.core.types import DialogueState as DialogueStateTypedDict
from soni.core.validators import validate_state_consistency, validate_transition

if TYPE_CHECKING:
    from soni.core.config import SoniConfig
    from soni.core.interfaces import IActionHandler, INLUProvider, INormalizer, IScopeManager
else:
    # Import for runtime (mypy needs these at runtime for type checking)
    from soni.core.interfaces import IActionHandler, INLUProvider, INormalizer, IScopeManager


@dataclass
class DialogueState:
    """Represents the state of a dialogue conversation."""

    messages: list[dict[str, str]] = field(default_factory=list)
    current_flow: str = "none"
    slots: dict[str, Any] = field(default_factory=dict)
    pending_action: str | None = None
    last_response: str = ""
    turn_count: int = 0
    trace: list[dict[str, Any]] = field(default_factory=list)
    summary: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert state to dictionary for serialization."""
        return asdict(self)

    def to_json(self) -> str:
        """Serialize state to JSON string."""
        return json.dumps(self.to_dict(), default=str)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> DialogueState:
        """Create DialogueState from dictionary."""
        return cls(
            messages=data.get("messages", []),
            current_flow=data.get("current_flow", "none"),
            slots=data.get("slots", {}),
            pending_action=data.get("pending_action"),
            last_response=data.get("last_response", ""),
            turn_count=data.get("turn_count", 0),
            trace=data.get("trace", []),
            summary=data.get("summary"),
        )

    @classmethod
    def from_json(cls, json_str: str) -> DialogueState:
        """Create DialogueState from JSON string."""
        data = json.loads(json_str)
        return cls.from_dict(data)

    def add_message(self, role: str, content: str) -> None:
        """Add a message to the conversation history."""
        self.messages.append({"role": role, "content": content})

    def get_user_messages(self) -> list[str]:
        """Get all user messages."""
        return [msg["content"] for msg in self.messages if msg.get("role") == "user"]

    def get_assistant_messages(self) -> list[str]:
        """Get all assistant messages."""
        return [msg["content"] for msg in self.messages if msg.get("role") == "assistant"]

    def get_slot(self, slot_name: str, default: Any = None) -> Any:
        """Get a slot value by name."""
        return self.slots.get(slot_name, default)

    def set_slot(self, slot_name: str, value: Any) -> None:
        """Set a slot value."""
        self.slots[slot_name] = value

    def has_slot(self, slot_name: str) -> bool:
        """Check if a slot is filled."""
        return slot_name in self.slots and self.slots[slot_name] is not None

    def clear_slots(self) -> None:
        """Clear all slots."""
        self.slots.clear()

    def increment_turn(self) -> None:
        """Increment turn counter."""
        self.turn_count += 1

    def add_trace(self, event: str, data: dict[str, Any]) -> None:
        """Add a trace event for debugging."""
        self.trace.append({"event": event, "data": data})


@dataclass
class RuntimeContext:
    """Runtime context containing configuration and dependencies.

    This class separates configuration and dependencies from dialogue state,
    maintaining clean separation of concerns and enabling proper serialization.

    Attributes:
        config: Soni configuration
        scope_manager: Scope manager for action filtering
        normalizer: Slot normalizer for value normalization
        action_handler: Handler for executing actions
        du: NLU provider for dialogue understanding
    """

    config: SoniConfig  # Use string annotation to avoid circular import
    scope_manager: IScopeManager
    normalizer: INormalizer
    action_handler: IActionHandler
    du: INLUProvider

    def get_slot_config(self, slot_name: str) -> Any:
        """Get configuration for a specific slot.

        Args:
            slot_name: Name of the slot

        Returns:
            Slot configuration

        Raises:
            KeyError: If slot not found in config
        """
        return self.config.slots[slot_name]

    def get_action_config(self, action_name: str) -> Any:
        """Get configuration for a specific action.

        Args:
            action_name: Name of the action

        Returns:
            Action configuration

        Raises:
            KeyError: If action not found in config
        """
        return self.config.actions[action_name]

    def get_flow_config(self, flow_name: str) -> Any:
        """Get configuration for a specific flow.

        Args:
            flow_name: Name of the flow

        Returns:
            Flow configuration

        Raises:
            KeyError: If flow not found in config
        """
        return self.config.flows[flow_name]


# Helper functions for TypedDict DialogueState (Phase 1)
# Note: The DialogueState dataclass above is still used in existing code
# and will be migrated in later phases. These helpers are for new code.


def create_empty_state() -> DialogueStateTypedDict:
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
        "nlu_result": None,
        "last_nlu_call": None,
        "digression_depth": 0,
        "last_digression_type": None,
        "turn_count": 0,
        "trace": [],
        "metadata": {},
    }


def create_initial_state(user_message: str) -> DialogueStateTypedDict:
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
    state: DialogueStateTypedDict,
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

    # Apply updates
    for key, value in updates.items():
        if key in state:
            state[key] = value  # type: ignore

    # Validate final state consistency
    if validate:
        validate_state_consistency(state)


def state_to_dict(state: DialogueStateTypedDict) -> dict[str, Any]:
    """
    Serialize DialogueState to JSON-compatible dict.

    Args:
        state: Dialogue state

    Returns:
        JSON-serializable dictionary
    """
    # DialogueState is already a dict (TypedDict), but ensure deep copy
    return copy.deepcopy(dict(state))


def state_from_dict(data: dict[str, Any]) -> DialogueStateTypedDict:
    """
    Deserialize DialogueState from dict.

    Args:
        data: Dictionary with state data

    Returns:
        DialogueState

    Raises:
        ValidationError: If data is invalid
    """
    # Validate required fields
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

    state: DialogueStateTypedDict = data  # type: ignore

    # Validate consistency
    validate_state_consistency(state)

    return state


def state_to_json(state: DialogueStateTypedDict) -> str:
    """Serialize state to JSON string."""
    return json.dumps(state_to_dict(state), indent=2)


def state_from_json(json_str: str) -> DialogueStateTypedDict:
    """Deserialize state from JSON string."""
    data = json.loads(json_str)
    return state_from_dict(data)
