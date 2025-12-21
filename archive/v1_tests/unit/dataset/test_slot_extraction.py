"""Tests for slot extraction dataset generation."""

from soni.dataset.base import DomainConfig, DomainExampleData
from soni.dataset.slot_extraction import SlotExtractionDatasetBuilder, SlotExtractionExampleTemplate
from soni.du.slot_extractor import SlotExtractionInput, SlotExtractionResult


class TestSlotExtractionDataset:
    """Tests for dataset builder."""

    def test_build_from_slot_values(self):
        """GIVEN domain with example values WHEN build THEN generates simple examples."""
        domain_config = DomainConfig(
            name="test_domain",
            description="Test",
            available_flows=["flow1"],
            flow_descriptions={"flow1": "desc"},
            available_actions=["action1"],
            slots={"amount": "float"},
            slot_prompts={"amount": "Amount"},
            example_data=DomainExampleData(slot_values={"amount": ["100", "50"]}),
        )

        builder = SlotExtractionDatasetBuilder()
        examples = builder.build(domain_config)

        assert len(examples) > 0
        assert isinstance(examples[0], SlotExtractionExampleTemplate)

        # Check content - we generate multiple templates per value
        found_100 = any("100" in ex.user_message for ex in examples)
        assert found_100

        # Check expected output
        ex = examples[0]
        assert len(ex.expected_output.extracted_slots) == 1
        assert ex.expected_output.extracted_slots[0]["slot"] == "amount"

    def test_build_from_extraction_cases(self):
        """GIVEN domain with slot_extraction_cases WHEN build THEN includes multi-slot examples."""
        domain_config = DomainConfig(
            name="test",
            description="Test",
            available_flows=[],
            flow_descriptions={},
            available_actions=[],
            slots={"amount": "float", "currency": "string"},
            slot_prompts={"amount": "Amount", "currency": "Currency"},
            example_data=DomainExampleData(
                slot_values={},
                slot_extraction_cases=[
                    (
                        "Send 100 USD",
                        [{"slot": "amount", "value": "100"}, {"slot": "currency", "value": "USD"}],
                    ),
                    ("Check balance", []),  # Negative example
                ],
            ),
        )

        builder = SlotExtractionDatasetBuilder()
        examples = builder.build(domain_config)

        # Should have exactly the cases we defined
        assert len(examples) == 2

        # First has 2 slots
        assert len(examples[0].expected_output.extracted_slots) == 2

        # Second is negative (no slots)
        assert len(examples[1].expected_output.extracted_slots) == 0

    def test_to_dspy_example(self):
        """GIVEN template WHEN to_dspy_example THEN returns correctly formatted Example."""
        template = SlotExtractionExampleTemplate(
            user_message="test",
            slot_definitions=[SlotExtractionInput(name="s", slot_type="str")],
            expected_output=SlotExtractionResult(extracted_slots=[]),
            domain="d",
            flow="f",
        )

        dspy_ex = template.to_dspy_example()

        assert dspy_ex.user_message == "test"
        assert len(dspy_ex.slot_definitions) == 1
        assert dspy_ex.result.extracted_slots == []
        # Check inputs set
        assert "user_message" in dspy_ex._input_keys
        assert "slot_definitions" in dspy_ex._input_keys

    def test_banking_domain_includes_currency(self):
        """GIVEN banking domain WHEN build THEN includes currency examples."""
        from soni.dataset.domains.banking import BANKING

        builder = SlotExtractionDatasetBuilder()
        examples = builder.build(BANKING)

        # Check that we have currency in some examples
        currency_examples = [
            ex
            for ex in examples
            if any(s.get("slot") == "currency" for s in ex.expected_output.extracted_slots)
        ]
        assert len(currency_examples) > 0, (
            "Should include currency examples from slot_extraction_cases"
        )
