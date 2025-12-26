"""Dataset generator for slot extraction optimization.

Generates training examples specifically for the SlotExtractor module (Pass 2 NLU).
Uses the slot_extraction_cases from DomainExampleData for domain-specific examples.
"""

import dspy
from pydantic import BaseModel

from soni.core.commands import SetSlot
from soni.dataset.base import DomainConfig
from soni.du.slot_extractor import SlotExtractionInput, SlotExtractionResult


class SlotExtractionExampleTemplate(BaseModel):
    """Template for creating a slot extraction example."""

    user_message: str
    slot_definitions: list[SlotExtractionInput]
    expected_output: SlotExtractionResult
    domain: str
    flow: str

    def to_dspy_example(self) -> dspy.Example:
        """Convert to dspy.Example."""
        return dspy.Example(
            user_message=self.user_message,
            slot_definitions=self.slot_definitions,
            result=self.expected_output,
        ).with_inputs("user_message", "slot_definitions")


class SlotExtractionDatasetBuilder:
    """Builder for slot extraction datasets.

    Generates examples from two sources:
    1. Single-slot examples from slot_values (simple templates)
    2. Multi-slot examples from slot_extraction_cases (domain-specific)
    """

    def build(self, domain_config: DomainConfig) -> list[SlotExtractionExampleTemplate]:
        """Generate slot extraction examples for a domain."""
        examples: list[SlotExtractionExampleTemplate] = []

        # 1. Generate single-slot examples from slot_values
        examples.extend(self._generate_from_slot_values(domain_config))

        # 2. Generate multi-slot examples from slot_extraction_cases
        examples.extend(self._generate_from_cases(domain_config))

        return examples

    def _generate_from_slot_values(
        self, domain_config: DomainConfig
    ) -> list[SlotExtractionExampleTemplate]:
        """Generate simple single-slot examples from slot_values."""
        examples: list[SlotExtractionExampleTemplate] = []

        if not domain_config.example_data or not domain_config.example_data.slot_values:
            return examples

        # Simple utterance templates
        templates = [
            "{}",
            "I want {}",
            "Make it {}",
            "Set to {}",
            "It is {}",
        ]

        for slot_name, values in domain_config.example_data.slot_values.items():
            slot_type = domain_config.slots.get(slot_name)
            if not slot_type:
                continue

            description = domain_config.slot_prompts.get(slot_name, "")

            slot_def = SlotExtractionInput(
                name=slot_name,
                slot_type=slot_type,
                description=description,
                examples=values[:3],
            )

            for val in values:
                for tmpl in templates:
                    msg = tmpl.format(val)
                    examples.append(
                        SlotExtractionExampleTemplate(
                            user_message=msg,
                            slot_definitions=[slot_def],
                            expected_output=SlotExtractionResult(
                                extracted_slots=[SetSlot(slot=slot_name, value=val)]
                            ),
                            domain=domain_config.name,
                            flow="generic",
                        )
                    )

        return examples

    def _generate_from_cases(
        self, domain_config: DomainConfig
    ) -> list[SlotExtractionExampleTemplate]:
        """Generate multi-slot examples from slot_extraction_cases."""
        examples: list[SlotExtractionExampleTemplate] = []

        cases = domain_config.example_data.slot_extraction_cases
        if not cases:
            return examples

        # Build full slot definitions from domain config
        slot_defs = [
            SlotExtractionInput(
                name=slot_name,
                slot_type=slot_type,
                description=domain_config.slot_prompts.get(slot_name, ""),
                examples=domain_config.example_data.slot_values.get(slot_name, [])[:3],
            )
            for slot_name, slot_type in domain_config.slots.items()
        ]

        for user_message, expected_slots in cases:
            examples.append(
                SlotExtractionExampleTemplate(
                    user_message=user_message,
                    slot_definitions=slot_defs,
                    expected_output=SlotExtractionResult(
                        extracted_slots=[
                            SetSlot(slot=s["slot"], value=s["value"]) for s in expected_slots
                        ]
                    ),
                    domain=domain_config.name,
                    flow="multi_slot",
                )
            )

        return examples
