"""CLARIFICATION pattern generator.

Asking why info is needed.

Examples:
    - "Why do you need my email?"
    - "What's this for?"

Refactored to use DomainExampleData for domain-agnostic generation.
"""

from typing import Literal

import dspy
from soni.core.commands import RequestClarification
from soni.dataset.base import (
    ConversationContext,
    DomainConfig,
    ExampleTemplate,
    PatternGenerator,
)
from soni.dataset.constants import DEFAULT_EXAMPLE_DATETIME
from soni.du.models import NLUOutput


class ClarificationGenerator(PatternGenerator):
    """Generates CLARIFICATION pattern examples.

    Uses domain_config.example_data for domain-agnostic generation.
    """

    # Common clarification questions
    CLARIFICATION_QUESTIONS = [
        "Why do you need that?",
        "What's this for?",
        "Why is that necessary?",
        "Can you explain why you need this information?",
        "What will you use this for?",
    ]

    def generate_examples(
        self,
        domain_config: DomainConfig,
        context_type: Literal["cold_start", "ongoing"],
        count: int = 3,
    ) -> list[ExampleTemplate]:
        """Generate CLARIFICATION examples (ongoing only)."""
        if context_type == "cold_start":
            return []  # Clarifications only happen in ongoing conversations

        return self._generate_ongoing_examples(domain_config, count)

    def _generate_ongoing_examples(
        self,
        domain_config: DomainConfig,
        count: int,
    ) -> list[ExampleTemplate]:
        """Generate clarification examples using domain_config.example_data."""
        examples = []

        primary_flow = domain_config.get_primary_flow()
        slot_names = list(domain_config.slots.keys())

        # Generate examples for each slot (asking about why it's needed)
        for i, slot_name in enumerate(slot_names[:count]):
            question = self.CLARIFICATION_QUESTIONS[i % len(self.CLARIFICATION_QUESTIONS)]

            # Build context with some slots already filled
            current_slots = {}
            for prev_slot in slot_names[:i]:
                values = domain_config.get_slot_values(prev_slot)
                if values:
                    current_slots[prev_slot] = values[0]

            examples.append(
                ExampleTemplate(
                    user_message=question,
                    conversation_context=ConversationContext(
                        history=dspy.History(messages=[{"user_message": f"Start {primary_flow}"}]),
                        current_slots=current_slots,
                        current_flow=primary_flow,
                        expected_slots=[slot_name],
                    ),
                    expected_output=NLUOutput(
                        commands=[RequestClarification(topic=f"reason for {slot_name}")],
                        confidence=0.9,
                    ),
                    domain=domain_config.name,
                    pattern="clarification",
                    context_type="ongoing",
                    current_datetime=DEFAULT_EXAMPLE_DATETIME,
                )
            )

            # Also add "What is X?" style questions
            examples.append(
                ExampleTemplate(
                    user_message=f"What is a {slot_name}?",
                    conversation_context=ConversationContext(
                        history=dspy.History(
                            messages=[{"user_message": f"I need to {primary_flow}"}]
                        ),
                        current_slots=current_slots,
                        current_flow=primary_flow,
                        expected_slots=[slot_name],
                    ),
                    expected_output=NLUOutput(
                        commands=[RequestClarification(topic=slot_name)],
                        confidence=0.9,
                    ),
                    domain=domain_config.name,
                    pattern="clarification",
                    context_type="ongoing",
                    current_datetime=DEFAULT_EXAMPLE_DATETIME,
                )
            )

        return examples[:count]
