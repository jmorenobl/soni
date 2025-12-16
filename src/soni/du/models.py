"""Pydantic models for DSPy signature types.

These models define the structured input/output for the NLU signature.
DSPy uses Pydantic for output validation and type coercion.
"""

from typing import Literal

from pydantic import BaseModel, Field, field_validator

from soni.core.commands import Command


class FlowInfo(BaseModel):
    """Information about an available flow."""

    name: str = Field(description="Flow identifier")
    description: str = Field(description="What this flow does")
    trigger_intents: list[str] = Field(
        default_factory=list, description="Example phrases that trigger this flow"
    )


class SlotValue(BaseModel):
    """A slot with its current value."""

    name: str = Field(description="Slot name")
    value: str | None = Field(description="Current value or None if not set")
    expected_type: str = Field(default="string", description="Expected type: string, date, number")


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
    current_slots: list[SlotValue] = Field(
        default_factory=list, description="Slots already filled in the current flow"
    )
    expected_slot: str | None = Field(
        default=None, description="Slot the system is currently asking for"
    )
    conversation_state: Literal["idle", "collecting", "confirming", "action_pending"] = Field(
        default="idle", description="Current conversation phase"
    )


class NLUOutput(BaseModel):
    """Structured output from NLU.

    Note: reasoning is NOT included here because ChainOfThough
    adds it automatically as a separate field.
    """

    commands: list[Command] = Field(description="List of commands to execute in order")
    confidence: float = Field(default=1.0, description="Confidence score")

    @field_validator("commands", mode="before")
    @classmethod
    def coerce_commands(cls, v: list) -> list[Command]:
        """Convert raw dicts or base Commands to proper subclasses."""
        from soni.core.commands import Command as BaseCommand

        result = []
        for item in v:
            if isinstance(item, dict):
                # Parse using registry
                result.append(BaseCommand.parse(item))
            elif isinstance(item, BaseCommand) and type(item) is BaseCommand:
                # It's a base Command, try to upgrade via registry
                data = item.model_dump()
                try:
                    result.append(BaseCommand.parse(data))
                except ValueError:
                    result.append(item)  # Keep as-is if can't parse
            else:
                result.append(item)
        return result
