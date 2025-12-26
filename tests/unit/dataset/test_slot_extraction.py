"""Tests for slot extraction dataset builder."""

import pytest

from soni.dataset.domains.banking import BANKING
from soni.dataset.slot_extraction import SlotExtractionDatasetBuilder, SlotExtractionExampleTemplate


def test_slot_extraction_builder_banking():
    """Should build slot extraction examples for banking domain."""
    builder = SlotExtractionDatasetBuilder()
    examples = builder.build(BANKING)

    assert len(examples) > 0
    assert all(isinstance(ex, SlotExtractionExampleTemplate) for ex in examples)

    # Check one example to_dspy_example
    dspy_ex = examples[0].to_dspy_example()
    assert dspy_ex.user_message == examples[0].user_message
    assert "slot_definitions" in dspy_ex
