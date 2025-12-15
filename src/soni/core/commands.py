"""Core Command definitions for Soni v2.0 (Command-Driven Architecture).

Commands are the deterministic output of the NLU layer (Dialogue Understanding)
and the input to the Dialogue Manager (CommandExecutor). They represent
EXPLICIT intentions or actions the user wants to perform.

Uses Pydantic discriminated unions for proper polymorphic serialization/deserialization.
"""

from typing import Annotated, Any, Literal

from pydantic import BaseModel, Field


class Command(BaseModel):
    """Base class for all commands."""

    type: str = Field(default="command", description="Command type discriminator")
    confidence: float = Field(
        default=1.0, ge=0.0, le=1.0, description="Confidence score of this command"
    )

    def __str__(self) -> str:
        return self.__class__.__name__


# --- Flow Management Commands ---


class StartFlow(Command):
    """Start a new flow."""

    type: Literal["start_flow"] = "start_flow"
    flow_name: str = Field(..., description="Name of the flow to start")
    slots: dict[str, Any] = Field(
        default_factory=dict, description="Initial slot values extracted with the start intent"
    )


class CancelFlow(Command):
    """Cancel the current flow."""

    type: Literal["cancel_flow"] = "cancel_flow"
    reason: str | None = Field(default=None, description="Reason for cancellation (optional)")


class HumanHandoff(Command):
    """Transfer conversation to a human agent."""

    type: Literal["human_handoff"] = "human_handoff"
    reason: str | None = Field(default=None, description="Reason for handoff")


# --- Slot Management Commands ---


class SetSlot(Command):
    """Set a slot value in the active flow."""

    type: Literal["set_slot"] = "set_slot"
    slot_name: str = Field(..., description="Name of the slot to set")
    value: Any = Field(..., description="Value to set")


class CorrectSlot(Command):
    """Correct a previously set slot value (Correction Pattern)."""

    type: Literal["correct_slot"] = "correct_slot"
    slot_name: str = Field(..., description="Name of the slot being corrected")
    new_value: Any = Field(..., description="The new correct value")


# --- Conversation Pattern Commands ---


class Clarify(Command):
    """User is asking for clarification about a prompt (Clarification Pattern)."""

    type: Literal["clarify"] = "clarify"
    topic: str | None = Field(default=None, description="What the user is asking about")
    original_text: str | None = Field(default=None, description="The user's clarification question")


class AffirmConfirmation(Command):
    """User affirmed a confirmation prompt (Certification/Confirmation Pattern)."""

    type: Literal["affirm_confirmation"] = "affirm_confirmation"


class DenyConfirmation(Command):
    """User denied a confirmation prompt (Certification/Confirmation Pattern)."""

    type: Literal["deny_confirmation"] = "deny_confirmation"
    slot_to_change: str | None = Field(
        default=None, description="If denial includes a modification, the slot to change"
    )


class OutOfScope(Command):
    """User input is outside the scope of the bot capabilities."""

    type: Literal["out_of_scope"] = "out_of_scope"
    topic: str | None = Field(default=None, description="The out-of-scope topic")


class ChitChat(Command):
    """User input is casual conversation not affecting flow."""

    type: Literal["chit_chat"] = "chit_chat"
    response_hint: str | None = Field(default=None, description="Suggested response or topic")


# Discriminated Union for proper polymorphic deserialization
AnyCommand = Annotated[
    StartFlow
    | CancelFlow
    | HumanHandoff
    | SetSlot
    | CorrectSlot
    | Clarify
    | AffirmConfirmation
    | DenyConfirmation
    | OutOfScope
    | ChitChat,
    Field(discriminator="type"),
]
