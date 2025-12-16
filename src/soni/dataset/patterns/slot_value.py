"""SLOT_VALUE pattern generator.

This pattern represents users providing direct answers to slot prompts
or providing multiple slots in a single utterance.

Examples:
    Cold start: "Book a flight from Madrid to Barcelona tomorrow"
    Ongoing: Bot: "Where to?" → User: "Barcelona"

Refactored to use DomainExampleData for domain-agnostic generation.
"""

from typing import Literal

import dspy

from soni.core.commands import SetSlot, StartFlow
from soni.dataset.base import (
    ConversationContext,
    DomainConfig,
    ExampleTemplate,
    PatternGenerator,
)
from soni.dataset.constants import DEFAULT_EXAMPLE_DATETIME
from soni.du.models import NLUOutput


class SlotValueGenerator(PatternGenerator):
    """Generates SLOT_VALUE pattern examples.

    Uses domain_config.example_data for domain-agnostic generation.
    """

    def generate_examples(
        self,
        domain_config: DomainConfig,
        context_type: Literal["cold_start", "ongoing"],
        count: int = 3,
    ) -> list[ExampleTemplate]:
        """Generate SLOT_VALUE examples."""
        if context_type == "cold_start":
            return self._generate_cold_start_examples(domain_config, count)
        else:
            return self._generate_ongoing_examples(domain_config, count)

    def _generate_cold_start_examples(
        self,
        domain_config: DomainConfig,
        count: int,
    ) -> list[ExampleTemplate]:
        """Generate cold start examples (multi-slot extraction)."""
        examples = []

        primary_flow = domain_config.get_primary_flow()
        slot_names = list(domain_config.slots.keys())

        # Generate multi-slot cold start examples
        # Take pairs of slots and create examples with both values
        for i in range(min(count, len(slot_names) - 1)):
            slot1 = slot_names[i]
            slot2 = slot_names[i + 1] if i + 1 < len(slot_names) else slot_names[0]

            values1 = domain_config.get_slot_values(slot1)
            values2 = domain_config.get_slot_values(slot2)

            if not values1 or not values2:
                continue

            val1 = values1[0]
            val2 = values2[0]

            # Create a natural multi-slot message
            user_message = f"I want to {primary_flow} with {slot1} {val1} and {slot2} {val2}"

            examples.append(
                ExampleTemplate(
                    user_message=user_message,
                    conversation_context=ConversationContext(
                        history=dspy.History(messages=[]),
                        current_slots={},
                        current_flow="none",
                        expected_slots=slot_names,
                    ),
                    expected_output=NLUOutput(
                        commands=[
                            StartFlow(flow_name=primary_flow),
                            SetSlot(slot=slot1, value=val1),
                            SetSlot(slot=slot2, value=val2),
                        ],
                        confidence=0.9,
                    ),
                    domain=domain_config.name,
                    pattern="slot_value",
                    context_type="cold_start",
                    current_datetime=DEFAULT_EXAMPLE_DATETIME,
                )
            )

        return examples[:count]

    def _generate_ongoing_examples(
        self,
        domain_config: DomainConfig,
        count: int,
    ) -> list[ExampleTemplate]:
        """Generate ongoing examples (single slot filling)."""
        examples = []

        primary_flow = domain_config.get_primary_flow()
        slot_names = list(domain_config.slots.keys())

        # Generate single-slot ongoing examples
        for i, slot_name in enumerate(slot_names[:count]):
            values = domain_config.get_slot_values(slot_name)
            if not values:
                continue

            value = values[0]

            # Build context with previous slots filled
            current_slots = {}
            for prev_slot in slot_names[:i]:
                prev_values = domain_config.get_slot_values(prev_slot)
                if prev_values:
                    current_slots[prev_slot] = prev_values[0]

            examples.append(
                ExampleTemplate(
                    user_message=value,  # User just provides the value
                    conversation_context=ConversationContext(
                        history=dspy.History(
                            messages=[{"user_message": f"I want to {primary_flow}"}]
                        ),
                        current_slots=current_slots,
                        current_flow=primary_flow,
                        expected_slots=[slot_name],
                    ),
                    expected_output=NLUOutput(
                        commands=[SetSlot(slot=slot_name, value=value)],
                        confidence=0.95,
                    ),
                    domain=domain_config.name,
                    pattern="slot_value",
                    context_type="ongoing",
                    current_datetime=DEFAULT_EXAMPLE_DATETIME,
                )
            )

        return examples[:count]
