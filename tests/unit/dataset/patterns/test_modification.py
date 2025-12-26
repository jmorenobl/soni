"""Tests for MODIFICATION pattern generator."""

import dspy
import pytest

from soni.dataset.domains.banking import BANKING
from soni.dataset.patterns.modification import ModificationGenerator


class TestModificationPattern:
    """Tests for ModificationGenerator."""

    def test_generates_modification_examples(self):
        """Generator should generate modification examples."""
        generator = ModificationGenerator()
        # Modifications are ongoing only
        examples = generator.generate_examples(BANKING, context_type="ongoing", count=3)

        assert len(examples) == 3
        assert all(ex.pattern == "modification" for ex in examples)

    def test_modification_includes_commands(self):
        """Examples should include CorrectSlot, DenyConfirmation, or SetSlot."""
        generator = ModificationGenerator()
        examples = generator.generate_examples(BANKING, context_type="ongoing", count=5)

        assert len(examples) >= 3
        command_names = {
            cmd.__class__.__name__ for ex in examples for cmd in ex.expected_output.commands
        }

        # Modification generator produces varied commands
        assert any(name in ["CorrectSlot", "DenyConfirmation", "SetSlot"] for name in command_names)
