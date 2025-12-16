"""DIGRESSION pattern generator.

Off-topic question without flow change.

Examples:
    - "What airlines fly that route?"
    - "Do you have direct flights?"

Refactored to use DomainExampleData for domain-agnostic generation.
"""

from typing import Literal

import dspy

from soni.core.commands import ChitChat
from soni.dataset.base import (
    ConversationContext,
    DomainConfig,
    ExampleTemplate,
    PatternGenerator,
)
from soni.dataset.constants import DEFAULT_EXAMPLE_DATETIME
from soni.du.models import NLUOutput


class DigressionGenerator(PatternGenerator):
    """Generates DIGRESSION pattern examples.

    Uses domain_config.example_data for domain-agnostic generation.
    """

    # Common digression questions (domain-agnostic)
    GENERIC_QUESTIONS = [
        "What are your fees?",
        "Is it safe?",
        "How long will this take?",
        "Do you have support?",
        "What are your hours?",
    ]

    def generate_examples(
        self,
        domain_config: DomainConfig,
        context_type: Literal["cold_start", "ongoing"],
        count: int = 3,
    ) -> list[ExampleTemplate]:
        """Generate DIGRESSION examples (ongoing only)."""
        if context_type == "cold_start":
            return []  # Digressions only happen in ongoing conversations

        return self._generate_ongoing_examples(domain_config, count)

    def _generate_ongoing_examples(
        self,
        domain_config: DomainConfig,
        count: int,
    ) -> list[ExampleTemplate]:
        """Generate digression examples using domain_config.example_data."""
        examples = []

        primary_flow = domain_config.get_primary_flow()
        slot_names = list(domain_config.slots.keys())

        for i, question in enumerate(self.GENERIC_QUESTIONS[:count]):
            # Build varying context for each example
            current_slots = {}
            expected_slot = slot_names[0] if slot_names else "info"

            # For later examples, add some filled slots
            if i > 0 and len(slot_names) > 1:
                first_slot = slot_names[0]
                values = domain_config.get_slot_values(first_slot)
                if values:
                    current_slots[first_slot] = values[0]
                expected_slot = slot_names[1] if len(slot_names) > 1 else slot_names[0]

            examples.append(
                ExampleTemplate(
                    user_message=question,
                    conversation_context=ConversationContext(
                        history=dspy.History(
                            messages=[{"user_message": f"I want to {primary_flow}"}]
                        ),
                        current_slots=current_slots,
                        current_flow=primary_flow,
                        expected_slots=[expected_slot],
                    ),
                    expected_output=NLUOutput(
                        commands=[ChitChat(message=question)],
                        confidence=0.85,
                    ),
                    domain=domain_config.name,
                    pattern="digression",
                    context_type="ongoing",
                    current_datetime=DEFAULT_EXAMPLE_DATETIME,
                )
            )

        return examples[:count]
