"""Tests for CLARIFICATION pattern generator."""

import dspy
import pytest

from soni.dataset.domains.banking import BANKING
from soni.dataset.patterns.clarification import ClarificationGenerator


class TestClarificationPattern:
    """Tests for ClarificationGenerator."""

    def test_generates_clarification_examples(self):
        """Generator should generate clarification examples."""
        generator = ClarificationGenerator()
        # Clarifications are ongoing only
        examples = generator.generate_examples(BANKING, context_type="ongoing", count=3)

        assert len(examples) == 3
        assert all(ex.pattern == "clarification" for ex in examples)

    def test_clarification_includes_request_clarification_command(self):
        """Examples should include RequestClarification command."""
        generator = ClarificationGenerator()
        examples = generator.generate_examples(BANKING, context_type="ongoing", count=1)

        assert len(examples) > 0
        cmd = examples[0].expected_output.commands[0]
        assert cmd.__class__.__name__ == "RequestClarification"
        assert hasattr(cmd, "topic")
