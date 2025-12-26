"""Tests for CORRECTION pattern generator."""

import dspy
import pytest

from soni.dataset.domains.banking import BANKING
from soni.dataset.patterns.correction import CorrectionGenerator


class TestCorrectionPattern:
    """Tests for CorrectionGenerator."""

    def test_generates_correction_examples(self):
        """Generator should generate correction examples."""
        generator = CorrectionGenerator()
        # Corrections are ongoing only
        examples = generator.generate_examples(BANKING, context_type="ongoing", count=3)

        assert len(examples) == 3
        assert all(ex.pattern == "correction" for ex in examples)

    def test_correction_includes_correct_slot_command(self):
        """Examples should include CorrectSlot command."""
        generator = CorrectionGenerator()
        examples = generator.generate_examples(BANKING, context_type="ongoing", count=1)

        assert len(examples) > 0
        cmd = examples[0].expected_output.commands[0]
        assert cmd.__class__.__name__ == "CorrectSlot"
        assert hasattr(cmd, "slot")
        assert hasattr(cmd, "new_value")

    def test_cold_start_correction_is_empty(self):
        """Corrections should not be generated for cold start."""
        generator = CorrectionGenerator()
        examples = generator.generate_examples(BANKING, context_type="cold_start", count=3)
        assert len(examples) == 0
