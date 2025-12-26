"""Tests for DIGRESSION pattern generator."""

import dspy
import pytest

from soni.dataset.domains.banking import BANKING
from soni.dataset.patterns.digression import DigressionGenerator


class TestDigressionPattern:
    """Tests for DigressionGenerator."""

    def test_generates_digression_examples(self):
        """Generator should generate digression examples."""
        generator = DigressionGenerator()
        # Digressions are ongoing only
        examples = generator.generate_examples(BANKING, context_type="ongoing", count=3)

        assert len(examples) == 3
        assert all(ex.pattern == "digression" for ex in examples)
        assert all(isinstance(ex.conversation_context.history, dspy.History) for ex in examples)

    def test_digression_includes_chitchat_command(self):
        """Examples should include ChitChat command."""
        generator = DigressionGenerator()
        examples = generator.generate_examples(BANKING, context_type="ongoing", count=1)

        assert len(examples) > 0
        cmd = examples[0].expected_output.commands[0]
        assert cmd.__class__.__name__ == "ChitChat"
        assert hasattr(cmd, "message")
