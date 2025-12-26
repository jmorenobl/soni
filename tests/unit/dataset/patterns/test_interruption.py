"""Tests for INTERRUPTION pattern generator."""

import dspy
import pytest

from soni.dataset.domains.banking import BANKING
from soni.dataset.patterns.interruption import InterruptionGenerator


class TestInterruptionPattern:
    """Tests for InterruptionGenerator."""

    def test_generates_interruption_examples(self):
        """Generator should generate interruption examples."""
        generator = InterruptionGenerator()
        examples = generator.generate_examples(BANKING, context_type="cold_start", count=3)

        assert len(examples) == 3
        assert all(ex.pattern == "interruption" for ex in examples)
        assert all(ex.context_type == "cold_start" for ex in examples)

    def test_interruption_includes_expected_command(self):
        """Examples should include StartFlow command."""
        generator = InterruptionGenerator()
        examples = generator.generate_examples(BANKING, context_type="cold_start", count=1)

        assert len(examples) > 0
        cmd = examples[0].expected_output.commands[0]
        assert cmd.__class__.__name__ == "StartFlow"
        assert hasattr(cmd, "flow_name")

    def test_ongoing_interruption(self):
        """Should switch flows in ongoing context."""
        generator = InterruptionGenerator()
        examples = generator.generate_examples(BANKING, context_type="ongoing", count=1)

        assert len(examples) == 1
        assert "actually" in examples[0].user_message.lower()
        assert examples[0].context_type == "ongoing"
