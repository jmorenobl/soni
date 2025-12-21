"""CANCELLATION pattern generator.

User abandons current task.

Examples:
    - "Cancel"
    - "Never mind"
    - "Forget it"

Refactored to use DomainExampleData for domain-agnostic generation.
"""

from typing import Literal

import dspy
from soni.core.commands import CancelFlow
from soni.dataset.base import (
    ConversationContext,
    DomainConfig,
    ExampleTemplate,
    PatternGenerator,
)
from soni.dataset.constants import DEFAULT_EXAMPLE_DATETIME
from soni.du.models import NLUOutput


class CancellationGenerator(PatternGenerator):
    """Generates CANCELLATION pattern examples.

    Uses domain_config.example_data for domain-agnostic generation.
    """

    # Common cancellation utterances
    CANCELLATION_PHRASES = [
        "Cancel",
        "Never mind",
        "Forget it",
        "Stop",
        "Cancel this",
        "Abort",
        "I changed my mind",
    ]

    def generate_examples(
        self,
        domain_config: DomainConfig,
        context_type: Literal["cold_start", "ongoing"],
        count: int = 3,
    ) -> list[ExampleTemplate]:
        """Generate CANCELLATION examples (ongoing only)."""
        if context_type == "cold_start":
            return []  # Cancellations only happen in ongoing conversations

        return self._generate_ongoing_examples(domain_config, count)

    def _generate_ongoing_examples(
        self,
        domain_config: DomainConfig,
        count: int,
    ) -> list[ExampleTemplate]:
        """Generate cancellation examples using domain_config.example_data."""
        examples = []

        primary_flow = domain_config.get_primary_flow()
        slot_names = list(domain_config.slots.keys())

        for i, phrase in enumerate(self.CANCELLATION_PHRASES[:count]):
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
                    user_message=phrase,
                    conversation_context=ConversationContext(
                        history=dspy.History(
                            messages=[{"user_message": f"I want to {primary_flow}"}]
                        ),
                        current_slots=current_slots,
                        current_flow=primary_flow,
                        expected_slots=[expected_slot],
                    ),
                    expected_output=NLUOutput(
                        commands=[CancelFlow(reason="User cancelled")],
                        confidence=0.9,
                    ),
                    domain=domain_config.name,
                    pattern="cancellation",
                    context_type="ongoing",
                    current_datetime=DEFAULT_EXAMPLE_DATETIME,
                )
            )

        return examples[:count]
