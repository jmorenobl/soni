"""Base classes for dataset construction."""

from typing import Any, Literal

import dspy
from pydantic import BaseModel, Field

from soni.du.models import DialogueContext, MessageType, NLUOutput


class DomainConfig(BaseModel):
    """Configuration for a business domain (e.g., flight booking).

    Defines the available flows, actions, and slots for a specific domain.
    This allows pattern generators to create contextually appropriate examples.
    """

    name: str = Field(description="Domain identifier (e.g., 'flight_booking')")
    description: str = Field(description="Human-readable description")
    available_flows: list[str] = Field(description="Flow names available in this domain")
    available_actions: list[str] = Field(description="Action names available in this domain")
    slots: dict[str, str] = Field(description="Slot name -> slot type mapping")
    slot_prompts: dict[str, str] = Field(description="Slot name -> prompt text mapping")

    model_config = {"frozen": True}  # Immutable


class ConversationContext(BaseModel):
    """Context for a conversation at a specific point in time.

    Captures the state of the conversation including history, current slots,
    active flow, and what slots are expected next.
    """

    history: dspy.History = Field(description="Conversation history")
    current_slots: dict[str, Any] = Field(
        default_factory=dict, description="Slots already filled in current flow"
    )
    current_flow: str = Field(default="none", description="Currently active flow name")
    expected_slots: list[str] = Field(
        default_factory=list, description="Slot names expected to be filled next"
    )
    conversation_state: str | None = Field(
        default=None,
        description="Current conversation state (e.g., 'confirming', 'waiting_for_slot')",
    )


class ExampleTemplate(BaseModel):
    """Template for creating a dspy.Example.

    This is an intermediate representation that can be converted to a
    dspy.Example with all the required fields properly structured.
    """

    user_message: str = Field(description="User's input message")
    conversation_context: ConversationContext = Field(description="Conversation state")
    expected_output: NLUOutput = Field(description="Expected NLU analysis")
    domain: str = Field(description="Domain name this example belongs to")
    pattern: str = Field(description="Pattern name this example demonstrates")
    context_type: Literal["cold_start", "ongoing"] = Field(
        description="Whether conversation has history"
    )
    current_datetime: str = Field(default="", description="Current datetime in ISO format")

    def to_dspy_example(self, domain_config: "DomainConfig") -> dspy.Example:
        """Convert to dspy.Example with proper format for optimization.

        Args:
            domain_config: Domain configuration to populate context

        Returns:
            dspy.Example ready for training/optimization
        """
        # Convert available_flows list to dict (flow_name -> flow_name)
        # DialogueContext expects dict[str, str] but DomainConfig has list[str]
        available_flows_dict = {flow: flow for flow in domain_config.available_flows}

        dialogue_context = DialogueContext(
            current_slots=self.conversation_context.current_slots,
            available_actions=domain_config.available_actions,
            available_flows=available_flows_dict,
            current_flow=self.conversation_context.current_flow,
            expected_slots=self.conversation_context.expected_slots,
            conversation_state=self.conversation_context.conversation_state,
        )

        return dspy.Example(
            user_message=self.user_message,
            history=self.conversation_context.history,
            context=dialogue_context,
            current_datetime=self.current_datetime,
            result=self.expected_output,
        ).with_inputs("user_message", "history", "context", "current_datetime")


class PatternGenerator:
    """Base class for pattern-specific example generators.

    Each subclass implements generation logic for a specific MessageType pattern
    (e.g., SLOT_VALUE, CORRECTION, INTERRUPTION).
    """

    @property
    def message_type(self) -> MessageType:
        """The MessageType this generator produces."""
        raise NotImplementedError("Subclasses must implement message_type property")

    def generate_examples(
        self,
        domain_config: DomainConfig,
        context_type: Literal["cold_start", "ongoing"],
        count: int = 3,
    ) -> list[ExampleTemplate]:
        """Generate N examples for this pattern + domain + context combination.

        Args:
            domain_config: Domain configuration
            context_type: "cold_start" (no history) or "ongoing" (with history)
            count: Number of examples to generate

        Returns:
            List of example templates
        """
        raise NotImplementedError("Subclasses must implement generate_examples()")
