"""Pydantic models for NLU inputs and outputs (v2.0)."""

from typing import Any

from pydantic import BaseModel, Field

from soni.core.commands import AnyCommand


class ExtractedEntity(BaseModel):
    """Raw entity/slot extracted from text."""

    name: str = Field(description="Name of the entity/slot")
    value: Any = Field(description="Extracted value")
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    original_text: str | None = Field(default=None, description="Original text span")


class NLUOutput(BaseModel):
    """Complete NLU analysis result (Command-Driven).

    The NLU layer now outputs a list of explicit Commands rather than
    a descriptive message type.
    """

    commands: list[AnyCommand] = Field(
        default_factory=list,
        description="List of commands to execute, in order.",
    )

    entities: list[ExtractedEntity] = Field(
        default_factory=list,
        description="Raw extracted entities suitable for highlighting or debugging.",
    )

    confidence: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Overall confidence of the interpretation.",
    )

    reasoning: str = Field(
        default="",
        description="Chain-of-thought reasoning for the generated commands.",
    )


class DialogueContext(BaseModel):
    """Current dialogue state provided to NLU for context-aware analysis."""

    current_slots: dict[str, Any] = Field(
        default_factory=dict,
        description="Already filled slots {slot_name: value}.",
    )

    available_actions: list[str] = Field(
        default_factory=list,
        description="Available action names in current context.",
    )

    available_flows: dict[str, str] = Field(
        default_factory=dict,
        description="Available flows as {flow_name: description}.",
    )

    current_flow: str = Field(
        default="none",
        description="Currently active flow name.",
    )

    expected_slots: list[str] = Field(
        default_factory=list,
        description="Slot names expected in current flow.",
    )

    current_prompted_slot: str | None = Field(
        default=None,
        description="Slot currently being asked for (if any).",
    )

    conversation_state: str | None = Field(
        default=None,
        description="Current conversation phase (e.g. 'confirming', 'waiting_for_slot').",
    )
