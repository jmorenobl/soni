"""MODIFICATION pattern generator.

Proactive modifications - user explicitly requests to change a value.

Examples:
    - "Change the destination to London"
    - "Can I modify the date?"

Refactored to use DomainExampleData for domain-agnostic generation.
"""

from typing import Literal

import dspy
from soni.core.commands import CorrectSlot, DenyConfirmation, SetSlot
from soni.dataset.base import (
    ConversationContext,
    DomainConfig,
    ExampleTemplate,
    PatternGenerator,
)
from soni.dataset.constants import DEFAULT_EXAMPLE_DATETIME
from soni.du.models import NLUOutput


class ModificationGenerator(PatternGenerator):
    """Generates MODIFICATION pattern examples.

    Uses domain_config.example_data for domain-agnostic generation.
    """

    def generate_examples(
        self,
        domain_config: DomainConfig,
        context_type: Literal["cold_start", "ongoing"],
        count: int = 3,
    ) -> list[ExampleTemplate]:
        """Generate MODIFICATION examples (ongoing only)."""
        if context_type == "cold_start":
            return []  # Modifications only happen in ongoing conversations

        return self._generate_ongoing_examples(domain_config, count)

    def _generate_ongoing_examples(
        self,
        domain_config: DomainConfig,
        count: int,
    ) -> list[ExampleTemplate]:
        """Generate modification examples using domain_config.example_data."""
        examples = []

        # Get slot names and their values from domain config
        slot_names = list(domain_config.slots.keys())
        primary_flow = domain_config.get_primary_flow()

        # Generate examples for each slot
        for _i, slot_name in enumerate(slot_names[:3]):  # Limit to first 3 slots
            slot_values = domain_config.get_slot_values(slot_name)
            if len(slot_values) < 2:
                continue

            old_value = slot_values[0]
            new_value = slot_values[1] if len(slot_values) > 1 else "new_value"

            # Example 1: "Change the {slot} to {new_value}"
            examples.append(
                ExampleTemplate(
                    user_message=f"Change the {slot_name} to {new_value}",
                    conversation_context=ConversationContext(
                        history=dspy.History(
                            messages=[{"user_message": f"Set {slot_name} to {old_value}"}]
                        ),
                        current_slots={slot_name: old_value},
                        current_flow=primary_flow,
                        expected_slots=[],
                    ),
                    expected_output=NLUOutput(
                        commands=[CorrectSlot(slot=slot_name, new_value=new_value)],
                        confidence=0.95,
                    ),
                    domain=domain_config.name,
                    pattern="modification",
                    context_type="ongoing",
                    current_datetime=DEFAULT_EXAMPLE_DATETIME,
                )
            )

            # Example 2: "Can I modify the {slot}?" (no new value - DenyConfirmation)
            examples.append(
                ExampleTemplate(
                    user_message=f"Can I modify the {slot_name}?",
                    conversation_context=ConversationContext(
                        history=dspy.History(
                            messages=[{"user_message": f"{slot_name}: {old_value}"}]
                        ),
                        current_slots={slot_name: old_value},
                        current_flow=primary_flow,
                        expected_slots=[],
                    ),
                    expected_output=NLUOutput(
                        commands=[DenyConfirmation(slot_to_change=slot_name)],
                        confidence=0.9,
                    ),
                    domain=domain_config.name,
                    pattern="modification",
                    context_type="ongoing",
                    current_datetime=DEFAULT_EXAMPLE_DATETIME,
                )
            )

            # Example 3: "No, change the {slot}" (denial with change request)
            examples.append(
                ExampleTemplate(
                    user_message=f"No, change the {slot_name}",
                    conversation_context=ConversationContext(
                        history=dspy.History(
                            messages=[{"user_message": f"Confirm {slot_name}: {old_value}?"}]
                        ),
                        current_slots={slot_name: old_value},
                        current_flow=primary_flow,
                        expected_slots=[],
                        conversation_state="confirming",
                    ),
                    expected_output=NLUOutput(
                        commands=[DenyConfirmation(slot_to_change=slot_name)],
                        confidence=0.9,
                    ),
                    domain=domain_config.name,
                    pattern="modification",
                    context_type="ongoing",
                    current_datetime=DEFAULT_EXAMPLE_DATETIME,
                )
            )

            # Example 4: Direct value modification during confirmation (e.g. "let's make 200")
            examples.append(
                ExampleTemplate(
                    user_message=f"actually make it {new_value}",
                    conversation_context=ConversationContext(
                        history=dspy.History(
                            messages=[{"user_message": f"Confirm {slot_name}: {old_value}?"}]
                        ),
                        current_slots={slot_name: old_value},
                        current_flow=primary_flow,
                        expected_slots=[],
                        conversation_state="confirming",
                    ),
                    expected_output=NLUOutput(
                        commands=[
                            SetSlot(slot=slot_name, value=new_value),
                        ],
                        confidence=0.9,
                    ),
                    domain=domain_config.name,
                    pattern="modification",
                    context_type="ongoing",
                    current_datetime=DEFAULT_EXAMPLE_DATETIME,
                )
            )

        return examples[:count]
