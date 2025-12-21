"""CONFIRMATION pattern generator.

Yes/no answers to confirmation prompts.

Examples:
    Positive: "Yes", "Correct", "That's right"
    Negative: "No", "That's wrong", "Incorrect"

Refactored to use DomainExampleData for domain-agnostic generation.
"""

from typing import Literal

import dspy
from soni.core.commands import AffirmConfirmation, DenyConfirmation
from soni.dataset.base import (
    ConversationContext,
    DomainConfig,
    ExampleTemplate,
    PatternGenerator,
)
from soni.dataset.constants import DEFAULT_EXAMPLE_DATETIME
from soni.du.models import NLUOutput


class ConfirmationGenerator(PatternGenerator):
    """Generates CONFIRMATION pattern examples.

    Uses domain_config.example_data for domain-agnostic generation.
    """

    def generate_examples(
        self,
        domain_config: DomainConfig,
        context_type: Literal["cold_start", "ongoing"],
        count: int = 3,
    ) -> list[ExampleTemplate]:
        """Generate CONFIRMATION examples (ongoing only)."""
        if context_type == "cold_start":
            return []  # Confirmations only happen in ongoing conversations

        return self._generate_ongoing_examples(domain_config, count)

    def _generate_ongoing_examples(
        self,
        domain_config: DomainConfig,
        count: int,
    ) -> list[ExampleTemplate]:
        """Generate confirmation examples using domain_config.example_data."""
        examples = []

        example_data = domain_config.example_data
        primary_flow = domain_config.get_primary_flow()

        # Create a confirmation context with all slots filled
        slot_names = list(domain_config.slots.keys())[:3]
        filled_slots = {}
        for slot_name in slot_names:
            values = domain_config.get_slot_values(slot_name)
            if values:
                filled_slots[slot_name] = values[0]

        confirmation_context = ConversationContext(
            history=dspy.History(messages=[{"user_message": f"Confirm: {filled_slots}?"}]),
            current_slots=filled_slots,
            current_flow=primary_flow,
            expected_slots=[],
            conversation_state="confirming",
        )

        # Generate positive confirmation examples
        for phrase in example_data.confirmation_positive[:2]:
            examples.append(
                ExampleTemplate(
                    user_message=phrase,
                    conversation_context=confirmation_context,
                    expected_output=NLUOutput(
                        commands=[AffirmConfirmation()],
                        confidence=0.95,
                    ),
                    domain=domain_config.name,
                    pattern="confirmation",
                    context_type="ongoing",
                    current_datetime=DEFAULT_EXAMPLE_DATETIME,
                )
            )

        # Generate negative confirmation examples
        for phrase in example_data.confirmation_negative[:2]:
            examples.append(
                ExampleTemplate(
                    user_message=phrase,
                    conversation_context=confirmation_context,
                    expected_output=NLUOutput(
                        commands=[DenyConfirmation()],
                        confidence=0.95,
                    ),
                    domain=domain_config.name,
                    pattern="confirmation",
                    context_type="ongoing",
                    current_datetime=DEFAULT_EXAMPLE_DATETIME,
                )
            )

        # Generate unclear confirmation examples (low confidence, no commands)
        for phrase in example_data.confirmation_unclear[:3]:
            examples.append(
                ExampleTemplate(
                    user_message=phrase,
                    conversation_context=confirmation_context,
                    expected_output=NLUOutput(
                        commands=[],  # No clear command
                        confidence=0.7,
                    ),
                    domain=domain_config.name,
                    pattern="confirmation",
                    context_type="ongoing",
                    current_datetime=DEFAULT_EXAMPLE_DATETIME,
                )
            )

        return examples[:count]
