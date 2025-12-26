"""Tests for CONFIRMATION pattern generator."""

import dspy
import pytest

from soni.dataset.domains.banking import BANKING
from soni.dataset.patterns.confirmation import ConfirmationGenerator


class TestConfirmationPattern:
    """Tests for ConfirmationGenerator."""

    def test_generates_confirmation_examples(self):
        """Generator should generate confirmation examples."""
        generator = ConfirmationGenerator()
        # Confirmations are ongoing only
        examples = generator.generate_examples(BANKING, context_type="ongoing", count=3)

        assert len(examples) == 3
        assert all(ex.pattern == "confirmation" for ex in examples)

    def test_confirmation_includes_expected_commands(self):
        """Examples should include AffirmConfirmation or DenyConfirmation."""
        generator = ConfirmationGenerator()
        # We need more examples to see both affirm and deny
        examples = generator.generate_examples(BANKING, context_type="ongoing", count=10)

        command_names = {
            cmd.__class__.__name__ for ex in examples for cmd in ex.expected_output.commands
        }
        assert "AffirmConfirmation" in command_names
        assert "DenyConfirmation" in command_names
