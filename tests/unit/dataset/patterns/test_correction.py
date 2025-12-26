from unittest.mock import MagicMock

import pytest

from soni.dataset.base import DomainConfig
from soni.dataset.patterns.correction import CorrectionGenerator


class TestCorrectionPattern:
    """Tests for correction pattern generation."""

    def test_generates_correction_examples(self):
        """Generator should generate correction examples."""
        generator = CorrectionGenerator()

        domain = MagicMock(spec=DomainConfig)
        domain.name = "test_domain"
        domain.get_primary_flow.return_value = "book_flight"
        domain.slots = {"destination": {}}
        domain.get_slot_values.return_value = ["Madrid", "Barcelona"]

        examples = generator.generate_examples(domain, context_type="ongoing", count=1)

        assert len(examples) == 1
        assert "Madrid" in examples[0].user_message or "Madrid" in str(
            examples[0].conversation_context.current_slots
        )

    def test_correction_includes_correct_slot_command(self):
        """Correction should include CorrectSlot command."""
        generator = CorrectionGenerator()
        domain = MagicMock(spec=DomainConfig)
        domain.name = "test_domain"
        domain.get_primary_flow.return_value = "book_flight"
        domain.slots = {"destination": {}}
        domain.get_slot_values.return_value = ["Madrid", "Barcelona"]

        examples = generator.generate_examples(domain, context_type="ongoing", count=1)

        commands = examples[0].expected_output.commands
        assert any(cmd.__class__.__name__ == "CorrectSlot" for cmd in commands)
