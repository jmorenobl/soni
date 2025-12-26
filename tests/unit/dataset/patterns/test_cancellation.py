from unittest.mock import MagicMock

import pytest

from soni.dataset.base import DomainConfig
from soni.dataset.patterns.cancellation import CancellationGenerator


class TestCancellationPattern:
    """Tests for cancellation pattern generation."""

    def test_generates_cancel_examples(self):
        """Pattern should generate cancellation examples."""
        generator = CancellationGenerator()

        # Mock DomainConfig
        domain = MagicMock(spec=DomainConfig)
        domain.name = "test_domain"
        domain.get_primary_flow.return_value = "book_flight"
        domain.slots = {"destination": "string"}

        examples = generator.generate_examples(domain, context_type="ongoing", count=3)

        assert len(examples) == 3
        # Check that it contains cancellation phrases
        assert any(
            p in examples[0].user_message for p in CancellationGenerator.CANCELLATION_PHRASES
        )

    def test_includes_expected_command(self):
        """Generated examples should include CancelFlow command."""
        generator = CancellationGenerator()
        domain = MagicMock(spec=DomainConfig)
        domain.name = "test_domain"
        domain.get_primary_flow.return_value = "book_flight"
        domain.slots = {}

        examples = generator.generate_examples(domain, context_type="ongoing", count=1)

        assert len(examples) > 0
        assert any(
            cmd.__class__.__name__ == "CancelFlow" for cmd in examples[0].expected_output.commands
        )
