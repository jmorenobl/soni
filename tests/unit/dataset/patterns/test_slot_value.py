"""Tests for SLOT_VALUE pattern generator."""

import dspy
import pytest

from soni.dataset.domains.banking import BANKING
from soni.dataset.patterns.slot_value import SlotValueGenerator


class TestSlotValuePattern:
    """Tests for SlotValueGenerator."""

    def test_generates_slot_value_examples(self):
        """Generator should generate slot_value examples."""
        generator = SlotValueGenerator()
        examples = generator.generate_examples(BANKING, context_type="cold_start", count=2)

        assert len(examples) == 2
        assert all(ex.pattern == "slot_value" for ex in examples)

    def test_ongoing_slot_filling(self):
        """Should fill single slots in ongoing context."""
        generator = SlotValueGenerator()
        examples = generator.generate_examples(BANKING, context_type="ongoing", count=3)

        assert len(examples) == 3
        assert all(examples[i].context_type == "ongoing" for i in range(3))
        # Expected output should be SetSlot
        assert examples[0].expected_output.commands[0].__class__.__name__ == "SetSlot"
