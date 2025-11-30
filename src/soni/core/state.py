"""Dialogue state management for Soni Framework"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from soni.core.config import SoniConfig
    from soni.core.interfaces import IActionHandler, INLUProvider, INormalizer, IScopeManager
else:
    # Import for runtime (mypy needs these at runtime for type checking)
    from soni.core.interfaces import IActionHandler, INLUProvider, INormalizer, IScopeManager


@dataclass
class DialogueState:
    """Represents the state of a dialogue conversation"""

    messages: list[dict[str, str]] = field(default_factory=list)
    current_flow: str = "none"
    slots: dict[str, Any] = field(default_factory=dict)
    pending_action: str | None = None
    last_response: str = ""
    turn_count: int = 0
    trace: list[dict[str, Any]] = field(default_factory=list)
    summary: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert state to dictionary for serialization"""
        return asdict(self)

    def to_json(self) -> str:
        """Serialize state to JSON string"""
        return json.dumps(self.to_dict(), default=str)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> DialogueState:
        """Create DialogueState from dictionary"""
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
        """Create DialogueState from JSON string"""
        data = json.loads(json_str)
        return cls.from_dict(data)

    def add_message(self, role: str, content: str) -> None:
        """Add a message to the conversation history"""
        self.messages.append({"role": role, "content": content})

    def get_user_messages(self) -> list[str]:
        """Get all user messages"""
        return [msg["content"] for msg in self.messages if msg.get("role") == "user"]

    def get_assistant_messages(self) -> list[str]:
        """Get all assistant messages"""
        return [msg["content"] for msg in self.messages if msg.get("role") == "assistant"]

    def get_slot(self, slot_name: str, default: Any = None) -> Any:
        """Get a slot value by name"""
        return self.slots.get(slot_name, default)

    def set_slot(self, slot_name: str, value: Any) -> None:
        """Set a slot value"""
        self.slots[slot_name] = value

    def has_slot(self, slot_name: str) -> bool:
        """Check if a slot is filled"""
        return slot_name in self.slots and self.slots[slot_name] is not None

    def clear_slots(self) -> None:
        """Clear all slots"""
        self.slots.clear()

    def increment_turn(self) -> None:
        """Increment turn counter"""
        self.turn_count += 1

    def add_trace(self, event: str, data: dict[str, Any]) -> None:
        """Add a trace event for debugging"""
        self.trace.append({"event": event, "data": data})


@dataclass
class RuntimeContext:
    """
    Runtime context containing configuration and dependencies.

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
        """
        Get configuration for a specific slot.

        Args:
            slot_name: Name of the slot

        Returns:
            Slot configuration

        Raises:
            KeyError: If slot not found in config
        """
        return self.config.slots[slot_name]

    def get_action_config(self, action_name: str) -> Any:
        """
        Get configuration for a specific action.

        Args:
            action_name: Name of the action

        Returns:
            Action configuration

        Raises:
            KeyError: If action not found in config
        """
        return self.config.actions[action_name]

    def get_flow_config(self, flow_name: str) -> Any:
        """
        Get configuration for a specific flow.

        Args:
            flow_name: Name of the flow

        Returns:
            Flow configuration

        Raises:
            KeyError: If flow not found in config
        """
        return self.config.flows[flow_name]
