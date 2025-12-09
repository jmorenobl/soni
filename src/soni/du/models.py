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
    """Structured NLU output.

    Attributes:
        message_type: Type of user message (slot_value, confirmation, correction, etc.)
        command: User's intent or command for intent changes, cancellations, confirmations
        slots: List of extracted slot values with metadata
        confidence: Overall extraction confidence (0.0 to 1.0)
        confirmation_value: For CONFIRMATION messages - True=yes, False=no, None=unclear

    Note:
        The confirmation_value field is only relevant when message_type is CONFIRMATION.
        It should be None for all other message types.
    """

    message_type: MessageType = Field(description="Type of user message")
    command: str | None = Field(
        default=None,
        description="User's intent or command when changing intent, canceling, or confirming. None for slot value messages.",
    )
    slots: list[SlotValue] = Field(default_factory=list, description="Extracted slot values")
    confidence: float = Field(ge=0.0, le=1.0, description="Overall confidence")
    confirmation_value: bool | None = Field(
        default=None,
        description=(
            "For CONFIRMATION message_type: True if user confirmed (yes/correct/confirm), "
            "False if user denied (no/wrong/incorrect), None if unclear or not a confirmation message."
        ),
    )


class DialogueContext(BaseModel):
    """Current dialogue context for NLU."""

    current_slots: dict[str, Any] = Field(default_factory=dict, description="Filled slots")
    available_actions: list[str] = Field(default_factory=list, description="Available actions")
    available_flows: dict[str, str] = Field(
        default_factory=dict, description="Available flows as {flow_name: description} mapping"
    )
    current_flow: str = Field(default="none", description="Active flow")
    expected_slots: list[str] = Field(default_factory=list, description="Expected slot names")
    current_prompted_slot: str | None = Field(
        default=None,
        description="Slot currently being prompted for - user's response should fill this slot",
    )
    conversation_state: str | None = Field(
        default=None,
        description=(
            "Current conversation state: idle, waiting_for_slot, confirming, "
            "ready_for_action, ready_for_confirmation, completed, etc."
        ),
    )
