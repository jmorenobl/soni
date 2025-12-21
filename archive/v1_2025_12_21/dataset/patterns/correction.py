"""CORRECTION pattern generator.

Reactive corrections - user realizes they made a mistake.

Examples:
    - Bot: "Flying to Madrid, correct?"
    - User: "No, I meant Barcelona"

Refactored to use DomainExampleData for domain-agnostic generation.
"""

from typing import Literal

import dspy
from soni.core.commands import CorrectSlot
from soni.dataset.base import (
    ConversationContext,
    DomainConfig,
    ExampleTemplate,
    PatternGenerator,
)
from soni.dataset.constants import DEFAULT_EXAMPLE_DATETIME
from soni.du.models import NLUOutput


class CorrectionGenerator(PatternGenerator):
    """Generates CORRECTION pattern examples.

    Uses domain_config.example_data for domain-agnostic generation.
    """

    # Common correction phrases
    CORRECTION_PATTERNS = [
        "No, I said {new_value} not {old_value}",
        "Actually, I meant {new_value}",
        "No, {new_value} instead",
        "I meant {new_value}",
        "Change to {new_value}",
    ]

    def generate_examples(
        self,
        domain_config: DomainConfig,
        context_type: Literal["cold_start", "ongoing"],
        count: int = 3,
    ) -> list[ExampleTemplate]:
        """Generate CORRECTION examples (ongoing only)."""
        if context_type == "cold_start":
            return []  # Corrections only happen in ongoing conversations

        return self._generate_ongoing_examples(domain_config, count)

    def _generate_ongoing_examples(
        self,
        domain_config: DomainConfig,
        count: int,
    ) -> list[ExampleTemplate]:
        """Generate correction examples using domain_config.example_data."""
        examples = []

        primary_flow = domain_config.get_primary_flow()
        slot_names = list(domain_config.slots.keys())

        for i, slot_name in enumerate(slot_names[:count]):
            slot_values = domain_config.get_slot_values(slot_name)
            if len(slot_values) < 2:
                continue

            old_value = slot_values[0]
            new_value = slot_values[1]

            # Select pattern based on index
            pattern = self.CORRECTION_PATTERNS[i % len(self.CORRECTION_PATTERNS)]
            user_message = pattern.format(old_value=old_value, new_value=new_value)

            # Build context with incorrect slot filled
            current_slots = {slot_name: old_value}

            # Determine next expected slot
            next_idx = min(i + 1, len(slot_names) - 1)
            expected_slot = slot_names[next_idx] if slot_names else "info"

            examples.append(
                ExampleTemplate(
                    user_message=user_message,
                    conversation_context=ConversationContext(
                        history=dspy.History(
                            messages=[{"user_message": f"{slot_name}: {old_value}"}]
                        ),
                        current_slots=current_slots,
                        current_flow=primary_flow,
                        expected_slots=[expected_slot],
                    ),
                    expected_output=NLUOutput(
                        commands=[CorrectSlot(slot=slot_name, new_value=new_value)],
                        confidence=0.9,
                    ),
                    domain=domain_config.name,
                    pattern="correction",
                    context_type="ongoing",
                    current_datetime=DEFAULT_EXAMPLE_DATETIME,
                )
            )

        return examples[:count]
