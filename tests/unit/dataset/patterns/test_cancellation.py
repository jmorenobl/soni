"""Tests for CANCELLATION pattern generator."""

import dspy
import pytest

from soni.dataset.domains.banking import BANKING
from soni.dataset.patterns.cancellation import CancellationGenerator


class TestCancellationPattern:
    """Tests for CancellationGenerator."""

    def test_generates_cancellation_examples(self):
        """Generator should generate cancellation examples."""
        generator = CancellationGenerator()
        # Cancellations are ongoing only
        examples = generator.generate_examples(BANKING, context_type="ongoing", count=3)

        assert len(examples) == 3
        assert all(ex.pattern == "cancellation" for ex in examples)

    def test_cancellation_includes_cancel_flow_command(self):
        """Examples should include CancelFlow command."""
        generator = CancellationGenerator()
        examples = generator.generate_examples(BANKING, context_type="ongoing", count=1)

        assert len(examples) > 0
        cmd = examples[0].expected_output.commands[0]
        # In v2.0 it's CancelFlow
        assert cmd.__class__.__name__ in ["CancelFlow", "CancelAction"]
