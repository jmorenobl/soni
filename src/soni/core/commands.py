"""Command hierarchy for DU → DM communication.

Commands represent user intent in a structured form.
The DM executes these deterministically.
"""
from typing import Any, Literal, ClassVar, Type
from pydantic import BaseModel, Field


class Command(BaseModel):
    """Base command from DU to DM.
    
    All commands must be serializable to dict for state storage.
    Uses registry pattern for automatic parsing.
    """
    
    type: str = Field(..., description="Discriminator field for command type")
    
    # Registry for all command subclasses
    _registry: ClassVar[dict[str, Type["Command"]]] = {}

    def __init_subclass__(cls, **kwargs: Any) -> None:
        """Automatically register subclasses based on type field default."""
        super().__init_subclass__(**kwargs)
        from typing import get_args, get_origin
        
    def __init_subclass__(cls, **kwargs: Any) -> None:
        """Automatically register subclasses based on type field default."""
        super().__init_subclass__(**kwargs)
        from typing import get_args, get_origin
        
        # Strategy: Inspect __annotations__ for Literal type
        if "type" in cls.__annotations__:
            annotation = cls.__annotations__["type"]
            if get_origin(annotation) is Literal:
                args = get_args(annotation)
                if args and isinstance(args[0], str):
                    Command._registry[args[0]] = cls

    @classmethod
    def parse(cls, data: dict[str, Any]) -> "Command":
        """Parse a dictionary into a typed Command object using the registry."""
        command_type = data.get("type")
        if not command_type:
             raise ValueError("Command data missing 'type' field")
             
        cmd_class = cls._registry.get(command_type)
        if not cmd_class:
             raise ValueError(f"Unknown command type: {command_type}")
             
        return cmd_class(**data)

    def model_dump(self, **kwargs: Any) -> dict[str, Any]:
        """Serialize command including type field."""
        return super().model_dump(**kwargs)


# Flow Control Commands

class StartFlow(Command):
    """Start a new flow."""
    
    type: Literal["start_flow"] = "start_flow"
    flow_name: str
    slots: dict[str, Any] = Field(default_factory=dict)


class CancelFlow(Command):
    """Cancel the current flow."""
    
    type: Literal["cancel_flow"] = "cancel_flow"
    reason: str | None = None


class CompleteFlow(Command):
    """Mark current flow as complete."""
    
    type: Literal["complete_flow"] = "complete_flow"


# Slot Commands

class SetSlot(Command):
    """Set a slot value."""
    
    type: Literal["set_slot"] = "set_slot"
    slot: str
    value: Any
    confidence: float = 1.0


class CorrectSlot(Command):
    """Correct a previously set slot."""
    
    type: Literal["correct_slot"] = "correct_slot"
    slot: str
    new_value: Any


class ClearSlot(Command):
    """Clear a slot value."""
    
    type: Literal["clear_slot"] = "clear_slot"
    slot: str


# Confirmation Commands

class AffirmConfirmation(Command):
    """User confirms (yes)."""
    
    type: Literal["affirm"] = "affirm"


class DenyConfirmation(Command):
    """User denies (no)."""
    
    type: Literal["deny"] = "deny"
    slot_to_change: str | None = None


# Conversation Commands

class RequestClarification(Command):
    """User requests clarification."""
    
    type: Literal["clarify"] = "clarify"
    topic: str | None = None


class ChitChat(Command):
    """Off-topic conversation."""
    
    type: Literal["chitchat"] = "chitchat"
    message: str | None = None


class HumanHandoff(Command):
    """Request human agent."""
    
    type: Literal["handoff"] = "handoff"
    reason: str | None = None


# Public parsing function
def parse_command(data: dict[str, Any]) -> Command:
    """Parse a serialized command dict back to Command object."""
    return Command.parse(data)
