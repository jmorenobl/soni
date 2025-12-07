"""Pydantic models for NLU inputs and outputs."""

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class MessageType(str, Enum):
    """Type of user message."""

    SLOT_VALUE = "slot_value"  # Direct answer to current prompt
    CORRECTION = "correction"  # Fixing a previous value
    MODIFICATION = "modification"  # Requesting to change a slot
    INTERRUPTION = "interruption"  # New intent/flow
    DIGRESSION = "digression"  # Question without flow change
    CLARIFICATION = "clarification"  # Asking for explanation
    CANCELLATION = "cancellation"  # Wants to stop
    CONFIRMATION = "confirmation"  # Yes/no to confirm prompt
    CONTINUATION = "continuation"  # General continuation


class SlotAction(str, Enum):
    """Action type for each individual slot extraction.

    This distinguishes between providing a new value vs correcting/modifying an existing one.
    Critical for proper dialogue management.
    """

    PROVIDE = "provide"  # Providing new slot value
    CORRECT = "correct"  # Correcting previous value (reactive)
    MODIFY = "modify"  # Explicitly requesting modification (proactive)
    CONFIRM = "confirm"  # Confirming a value


class SlotValue(BaseModel):
    """Extracted slot value with metadata."""

    name: str = Field(description="Slot name - MUST be one of the names in context.expected_slots")
    value: Any = Field(description="Extracted value from user message")
    confidence: float = Field(ge=0.0, le=1.0, description="Extraction confidence")
    # NOTE: Action type for this specific slot
    action: SlotAction = Field(
        default=SlotAction.PROVIDE,
        description="What action this slot represents: provide new, correct previous, modify, confirm",
    )
    # NOTE: Track previous value for corrections/modifications
    previous_value: Any | None = Field(
        default=None, description="Previous value if this is a correction/modification"
    )


class NLUOutput(BaseModel):
    """Structured NLU output."""

    message_type: MessageType = Field(description="Type of user message")
    command: str = Field(description="User's intent/command")
    slots: list[SlotValue] = Field(default_factory=list, description="Extracted slot values")
    confidence: float = Field(ge=0.0, le=1.0, description="Overall confidence")
    reasoning: str = Field(description="Step-by-step reasoning")


class DialogueContext(BaseModel):
    """Current dialogue context for NLU."""

    current_slots: dict[str, Any] = Field(default_factory=dict, description="Filled slots")
    available_actions: list[str] = Field(default_factory=list, description="Available actions")
    available_flows: list[str] = Field(default_factory=list, description="Available flows")
    current_flow: str = Field(default="none", description="Active flow")
    expected_slots: list[str] = Field(default_factory=list, description="Expected slot names")
    current_prompted_slot: str | None = Field(
        default=None,
        description="Slot currently being prompted for - user's response should fill this slot",
    )
