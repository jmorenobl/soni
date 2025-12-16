"""INTERRUPTION pattern generator.

User starts new task mid-conversation or at conversation start.

Examples:
    Cold start: "I want to book a flight"
    Ongoing: "Actually, check hotel prices first"

Refactored to use DomainExampleData for domain-agnostic generation.
"""

from typing import Literal

import dspy

from soni.core.commands import StartFlow
from soni.dataset.base import (
    ConversationContext,
    DomainConfig,
    ExampleTemplate,
    PatternGenerator,
)
from soni.dataset.constants import DEFAULT_EXAMPLE_DATETIME
from soni.du.models import NLUOutput


class InterruptionGenerator(PatternGenerator):
    """Generates INTERRUPTION pattern examples.

    Uses domain_config.example_data for domain-agnostic generation.
    """

    def generate_examples(
        self,
        domain_config: DomainConfig,
        context_type: Literal["cold_start", "ongoing"],
        count: int = 3,
    ) -> list[ExampleTemplate]:
        """Generate INTERRUPTION examples (both contexts)."""
        if context_type == "cold_start":
            return self._generate_cold_start_examples(domain_config, count)
        else:
            return self._generate_ongoing_examples(domain_config, count)

    def _generate_cold_start_examples(
        self,
        domain_config: DomainConfig,
        count: int,
    ) -> list[ExampleTemplate]:
        """Generate cold start interruption examples."""
        examples = []

        example_data = domain_config.example_data

        # Get trigger intents for each flow
        for flow_name, trigger_intents in example_data.trigger_intents.items():
            if not trigger_intents:
                continue

            for trigger in trigger_intents[:count]:
                examples.append(
                    ExampleTemplate(
                        user_message=trigger,
                        conversation_context=ConversationContext(
                            history=dspy.History(messages=[]),
                            current_slots={},
                            current_flow="none",
                            expected_slots=[],
                        ),
                        expected_output=NLUOutput(
                            commands=[StartFlow(flow_name=flow_name)],
                            confidence=0.9,
                        ),
                        domain=domain_config.name,
                        pattern="interruption",
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
        """Generate ongoing interruption examples (switching tasks)."""
        examples = []

        example_data = domain_config.example_data
        primary_flow = domain_config.get_primary_flow()
        # flow_names not used
        slot_names = list(domain_config.slots.keys())

        # Generate examples for switching between flows
        for _i, (flow_name, triggers) in enumerate(example_data.trigger_intents.items()):
            if not triggers or flow_name == primary_flow:
                continue

            # Build context of being in primary flow
            current_slots = {}
            if slot_names:
                first_slot = slot_names[0]
                values = domain_config.get_slot_values(first_slot)
                if values:
                    current_slots[first_slot] = values[0]

            expected_slot = (
                slot_names[1] if len(slot_names) > 1 else (slot_names[0] if slot_names else "info")
            )

            # Create switch message
            switch_msg = f"Actually, {triggers[0].lower()} instead"

            examples.append(
                ExampleTemplate(
                    user_message=switch_msg,
                    conversation_context=ConversationContext(
                        history=dspy.History(
                            messages=[{"user_message": f"I want to {primary_flow}"}]
                        ),
                        current_slots=current_slots,
                        current_flow=primary_flow,
                        expected_slots=[expected_slot],
                    ),
                    expected_output=NLUOutput(
                        commands=[StartFlow(flow_name=flow_name)],
                        confidence=0.85,
                    ),
                    domain=domain_config.name,
                    pattern="interruption",
                    context_type="ongoing",
                    current_datetime=DEFAULT_EXAMPLE_DATETIME,
                )
            )

        return examples[:count]
