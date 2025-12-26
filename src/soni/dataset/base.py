"""Base classes for dataset construction."""

from typing import Any, Literal

import dspy
from pydantic import BaseModel, Field

from soni.dataset.constants import (
    DEFAULT_EXAMPLE_DATETIME,
    SHARED_CONFIRMATION_NEGATIVE,
    SHARED_CONFIRMATION_POSITIVE,
    SHARED_CONFIRMATION_UNCLEAR,
)
from soni.du.models import DialogueContext, NLUOutput


class DomainExampleData(BaseModel):
    """Domain-specific data for generating training examples.

    This class encapsulates all the example values and utterance templates
    needed by pattern generators, eliminating if/elif chains per domain.
    """

    # Slot-specific example values (slot_name -> list of possible values)
    slot_values: dict[str, list[str]] = Field(
        default_factory=dict,
        description="Mapping of slot names to example values",
    )

    # Utterance templates for different patterns (pattern -> list of templates)
    utterance_templates: dict[str, list[str]] = Field(
        default_factory=dict,
        description="Mapping of pattern names to utterance templates",
    )

    # Trigger intents for flow interruption examples
    trigger_intents: dict[str, list[str]] = Field(
        default_factory=dict,
        description="Mapping of flow names to trigger intent phrases",
    )

    # Confirmation phrases (can override shared defaults)
    confirmation_positive: list[str] = Field(
        default_factory=lambda: list(SHARED_CONFIRMATION_POSITIVE),
        description="Positive confirmation phrases",
    )
    confirmation_negative: list[str] = Field(
        default_factory=lambda: list(SHARED_CONFIRMATION_NEGATIVE),
        description="Negative confirmation phrases",
    )
    confirmation_unclear: list[str] = Field(
        default_factory=lambda: list(SHARED_CONFIRMATION_UNCLEAR),
        description="Unclear/ambiguous confirmation phrases",
    )

    # Multi-slot extraction examples for SlotExtractor training
    # Each tuple: (user_message, list of {slot, value} dicts)
    slot_extraction_cases: list[tuple[str, list[dict[str, str]]]] = Field(
        default_factory=list,
        description="(message, expected_slots) pairs for slot extraction optimization",
    )

    def get_slot_values(self, slot_name: str) -> list[str]:
        """Get example values for a slot, with fallback defaults."""
        return self.slot_values.get(slot_name, ["value1", "value2", "value3"])

    def get_trigger_intents(self, flow_name: str) -> list[str]:
        """Get trigger intents for a flow."""
        return self.trigger_intents.get(flow_name, [])


class DomainConfig(BaseModel):
    """Configuration for a business domain (e.g., flight booking).

    Defines the available flows, actions, and slots for a specific domain.
    This allows pattern generators to create contextually appropriate examples.
    """

    name: str = Field(description="Domain identifier (e.g., 'flight_booking')")
    description: str = Field(description="Human-readable description")
    available_flows: list[str] = Field(description="Flow names available in this domain")
    flow_descriptions: dict[str, str] = Field(
        default_factory=dict, description="Flow name -> description mapping for semantic matching"
    )
    available_actions: list[str] = Field(description="Action names available in this domain")
    slots: dict[str, str] = Field(description="Slot name -> slot type mapping")
    slot_prompts: dict[str, str] = Field(description="Slot name -> prompt text mapping")

    # NEW: Domain-specific example data for pattern generators
    example_data: DomainExampleData = Field(
        default_factory=DomainExampleData,
        description="Domain-specific values for training example generation",
    )

    model_config = {"frozen": True}  # Immutable

    def get_slot_values(self, slot_name: str) -> list[str]:
        """Get example values for a specific slot.

        Convenience method for pattern generators.
        """
        return self.example_data.get_slot_values(slot_name)

    def get_trigger_intents(self, flow_name: str) -> list[str]:
        """Get trigger intents for a specific flow.

        Convenience method for pattern generators.
        """
        return self.example_data.get_trigger_intents(flow_name)

    def get_primary_flow(self) -> str:
        """Get the primary (first) flow name for this domain."""
        return self.available_flows[0] if self.available_flows else "unknown"

    def create_example(
        self,
        user_message: str,
        context: "ConversationContext",
        expected_output: "NLUOutput",
        pattern: str,
        context_type: Literal["cold_start", "ongoing"] = "ongoing",
    ) -> "ExampleTemplate":
        """Factory method to create ExampleTemplate with domain defaults.

        This method reduces boilerplate by automatically setting:
        - domain name
        - current_datetime from constants

        Args:
            user_message: User utterance
            context: Conversation context
            expected_output: Expected NLU output
            pattern: Pattern name (e.g., "slot_value", "correction")
            context_type: Context type

        Returns:
            ExampleTemplate with domain defaults
        """
        return ExampleTemplate(
            user_message=user_message,
            conversation_context=context,
            expected_output=expected_output,
            domain=self.name,
            pattern=pattern,
            context_type=context_type,
            current_datetime=DEFAULT_EXAMPLE_DATETIME,
        )


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
        from soni.du.models import CommandInfo, FlowInfo, SlotDefinition, SlotValue

        # Convert available_flows to list[FlowInfo]
        available_flows = [
            FlowInfo(
                name=flow,
                description=domain_config.flow_descriptions.get(flow, flow),
                trigger_intents=domain_config.example_data.trigger_intents.get(flow, []),
            )
            for flow in domain_config.available_flows
        ]

        # Generate flow_slots from domain config
        # This provides the LLM with type information for each slot
        flow_slots = [
            SlotDefinition(
                name=slot_name,
                slot_type=slot_type,
                description=domain_config.slot_prompts.get(slot_name, ""),
                required=True,  # Could be enhanced with domain config
                examples=domain_config.example_data.slot_values.get(slot_name, [])[:3],
            )
            for slot_name, slot_type in domain_config.slots.items()
        ]

        # Generate available_commands based on available actions
        # NOTE: command_type must match the Literal type in commands.py registry
        available_commands = [
            CommandInfo(
                command_type="start_flow",
                description="Start a new flow",
                required_fields=["flow_name"],
            ),
            CommandInfo(
                command_type="set_slot",
                description="Set a slot value",
                required_fields=["slot", "value"],
            ),
            CommandInfo(
                command_type="cancel_flow",
                description="Cancel the current flow",
                required_fields=[],
            ),
            CommandInfo(
                command_type="affirm",
                description="Confirm a pending action (user says yes)",
                required_fields=[],
            ),
            CommandInfo(
                command_type="deny",
                description="Deny a pending action (user says no)",
                required_fields=["slot_to_change"],
            ),
            CommandInfo(
                command_type="correct_slot",
                description="Correct a previously set slot value",
                required_fields=["slot", "new_value"],
            ),
            CommandInfo(
                command_type="clarify",
                description="User requests clarification about something",
                required_fields=[],
            ),
            CommandInfo(
                command_type="chitchat",
                description="Off-topic conversation or small talk",
                required_fields=[],
            ),
        ]

        # Convert current_slots dict to list[SlotValue]
        current_slots = [
            SlotValue(
                name=name,
                value=value,
                expected_type=domain_config.slots.get(name, "string"),
            )
            for name, value in self.conversation_context.current_slots.items()
        ]

        # Map conversation_state to valid Literal values
        # Auto-infer state if not explicitly set
        ConversationStateLiteral = Literal["idle", "collecting", "confirming", "action_pending"]

        raw_state = self.conversation_context.conversation_state

        # Auto-infer state based on context if not explicitly set
        if raw_state is None or raw_state == "":
            if (
                self.conversation_context.current_flow != "none"
                and self.conversation_context.expected_slots
            ):
                # Active flow with expected slots = collecting
                raw_state = "collecting"
            elif self.conversation_context.current_flow != "none":
                # Active flow, no expected slots = could be confirming or action pending
                raw_state = "collecting"  # Default to collecting, explicit confirming should be set
            else:
                raw_state = "idle"

        state_mapping: dict[str | None, ConversationStateLiteral] = {
            "idle": "idle",
            "none": "idle",
            "collecting": "collecting",
            "waiting_for_slot": "collecting",
            "confirming": "confirming",
            "action_pending": "action_pending",
        }
        conversation_state: ConversationStateLiteral = state_mapping.get(raw_state, "collecting")

        # Get first expected slot (new schema uses single slot, not list)
        expected_slots = self.conversation_context.expected_slots
        expected_slot = expected_slots[0] if expected_slots else None

        dialogue_context = DialogueContext(
            available_flows=available_flows,
            available_commands=available_commands,
            active_flow=self.conversation_context.current_flow
            if self.conversation_context.current_flow != "none"
            else None,
            flow_slots=flow_slots,
            current_slots=current_slots,
            expected_slot=expected_slot,
            conversation_state=conversation_state,
        )

        # Pass history as list[dict], not dspy.History
        # CommandGenerator.forward() handles the conversion to dspy.History
        history_messages = (
            self.conversation_context.history.messages
            if hasattr(self.conversation_context.history, "messages")
            else []
        )

        return dspy.Example(
            user_message=self.user_message,
            history=history_messages,
            context=dialogue_context,
            result=self.expected_output,
        ).with_inputs("user_message", "history", "context")


class PatternGenerator:
    """Base class for pattern-specific example generators.

    Each subclass implements generation logic for a specific MessageType pattern
    (e.g., SLOT_VALUE, CORRECTION, INTERRUPTION).
    """

    # Removed message_type property in v2.0 command implementation
    # @property
    # def message_type(self) -> MessageType:
    #    ...

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
