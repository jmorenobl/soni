"""
Pydantic models for Dialogue Understanding (DU) module.

DSPy uses Pydantic for output validation and type coercion.
"""

from typing import Annotated, Literal

from pydantic import BaseModel, Field

from soni.core.commands import (
    AffirmConfirmation,
    CancelFlow,
    ChitChat,
    CorrectSlot,
    DenyConfirmation,
    RequestClarification,
    SetSlot,
    StartFlow,
)


class FlowInfo(BaseModel):
    """Information about an available flow."""

    name: str = Field(description="Flow identifier")
    description: str = Field(description="What this flow does")
    trigger_intents: list[str] = Field(
        default_factory=list, description="Example phrases that trigger this flow"
    )

    def __str__(self) -> str:
        intents = (
            f" (Trigger intents: {', '.join(self.trigger_intents)})" if self.trigger_intents else ""
        )
        return f"- {self.name}: {self.description}{intents}"


class SlotValue(BaseModel):
    """A slot with its current value."""

    name: str = Field(description="Slot name")
    value: str | None = Field(description="Current value or None if not set")
    expected_type: str = Field(default="string", description="Expected type: string, date, number")

    def __str__(self) -> str:
        val = f"'{self.value}'" if self.value is not None else "None"
        return f"{self.name}={val} ({self.expected_type})"


class SlotDefinition(BaseModel):
    """Definition of a slot in the current flow.

    Provides type information so the LLM knows what kind of value to extract.
    """

    name: str = Field(description="Slot identifier")
    slot_type: str = Field(
        description="Data type: string, number, date, datetime, city, currency, email, phone, etc."
    )
    description: str = Field(default="", description="Human description of what this slot expects")
    required: bool = Field(default=True, description="Whether this slot must be filled")
    examples: list[str] = Field(
        default_factory=list, description="Example valid values for this slot"
    )

    def __str__(self) -> str:
        req = "required" if self.required else "optional"
        examples_str = f" (e.g., {', '.join(self.examples[:3])})" if self.examples else ""
        return f"- {self.name} ({self.slot_type}, {req}): {self.description}{examples_str}"


class CommandInfo(BaseModel):
    """Information about an available command.

    Passed dynamically to the LLM so it knows what commands it can generate.
    """

    command_type: str = Field(description="Command identifier (e.g., 'start_flow')")
    description: str = Field(description="What this command does")
    required_fields: list[str] = Field(
        default_factory=list, description="Fields required when using this command"
    )
    example: str = Field(
        default="", description="Example user message that would trigger this command"
    )

    def __str__(self) -> str:
        req = f" [Required: {', '.join(self.required_fields)}]" if self.required_fields else ""
        ex = f" (e.g., '{self.example}')" if self.example else ""
        return f"- {self.command_type}: {self.description}{req}{ex}"


class DialogueContext(BaseModel):
    """Complete dialogue context for NLU.

    Provides all information the LLM needs to understand user intent.
    """

    available_flows: list[FlowInfo] = Field(
        description="Flows the user can start. Each has name, description, and trigger examples"
    )
    available_commands: list[CommandInfo] = Field(
        description="Commands the LLM can generate. Each has type, description, required_fields"
    )
    active_flow: str | None = Field(
        default=None, description="Currently active flow name, or None if idle"
    )
    flow_slots: list[SlotDefinition] = Field(
        default_factory=list,
        description="All slots in the current flow with their types and descriptions",
    )
    current_slots: list[SlotValue] = Field(
        default_factory=list, description="Slots already filled in the current flow"
    )
    expected_slot: str | None = Field(
        default=None, description="Slot the system is currently asking for"
    )
    conversation_state: Literal["idle", "collecting", "confirming", "action_pending"] = Field(
        default="idle", description="Current conversation phase"
    )

    def __str__(self) -> str:
        lines = ["CONTEXT:"]

        lines.append(f"State: {self.conversation_state}")
        if self.active_flow:
            lines.append(f"Active Flow: {self.active_flow}")
        if self.expected_slot:
            lines.append(f"Expected Slot: {self.expected_slot}")

        if self.flow_slots:
            lines.append("Flow Slots (available in current flow):")
            for slot_def in self.flow_slots:
                lines.append(f"  {slot_def}")

        if self.current_slots:
            lines.append("Current Slots (already filled):")
            for slot in self.current_slots:
                lines.append(f"  {slot}")

        lines.append("Available Flows:")
        for flow in self.available_flows:
            lines.append(f"  {flow}")

        lines.append("Available Commands:")
        for cmd in self.available_commands:
            lines.append(f"  {cmd}")

        return "\n".join(lines)


# Type alias for discriminated union of command types
# This ensures DSPy generates proper JSON schema with all command fields
CommandUnion = Annotated[
    StartFlow
    | SetSlot
    | CorrectSlot
    | CancelFlow
    | AffirmConfirmation
    | DenyConfirmation
    | RequestClarification
    | ChitChat,
    Field(discriminator="type"),
]


class NLUOutput(BaseModel):
    """Structured output from NLU.

    Note: reasoning is NOT included here because ChainOfThought
    adds it automatically as a separate field.
    """

    # Use discriminated union for proper JSON schema generation
    # This ensures the LLM sees all fields required for each command type
    commands: list[CommandUnion] = Field(description="List of commands to execute in order")
    confidence: float = Field(default=1.0, description="Confidence score")
