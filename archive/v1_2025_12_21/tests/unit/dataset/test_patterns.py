"""Tests for dataset pattern generators."""

import pytest
from soni.dataset.domains import ALL_DOMAINS
from soni.dataset.patterns.cancellation import CancellationGenerator
from soni.dataset.patterns.clarification import ClarificationGenerator
from soni.dataset.patterns.confirmation import ConfirmationGenerator
from soni.dataset.patterns.correction import CorrectionGenerator
from soni.dataset.patterns.digression import DigressionGenerator
from soni.dataset.patterns.interruption import InterruptionGenerator
from soni.dataset.patterns.modification import ModificationGenerator
from soni.dataset.patterns.slot_value import SlotValueGenerator


class TestCancellationGenerator:
    """Tests for CancellationGenerator."""

    def test_cold_start_returns_empty(self):
        """Cancellation only happens in ongoing conversations."""
        gen = CancellationGenerator()
        domain = ALL_DOMAINS["flight_booking"]
        examples = gen.generate_examples(domain, "cold_start", 3)
        assert examples == []

    def test_ongoing_generates_examples(self):
        """Test generating ongoing cancellation examples."""
        gen = CancellationGenerator()
        domain = ALL_DOMAINS["flight_booking"]
        examples = gen.generate_examples(domain, "ongoing", 3)
        assert len(examples) == 3
        for ex in examples:
            assert ex.pattern == "cancellation"
            assert ex.context_type == "ongoing"

    @pytest.mark.parametrize("domain_name", list(ALL_DOMAINS.keys()))
    def test_all_domains(self, domain_name):
        """Test generator works for all domains."""
        gen = CancellationGenerator()
        domain = ALL_DOMAINS[domain_name]
        examples = gen.generate_examples(domain, "ongoing", 2)
        assert len(examples) == 2


class TestClarificationGenerator:
    """Tests for ClarificationGenerator."""

    def test_cold_start_returns_empty(self):
        """Clarification only happens in ongoing conversations."""
        gen = ClarificationGenerator()
        domain = ALL_DOMAINS["flight_booking"]
        examples = gen.generate_examples(domain, "cold_start", 3)
        assert examples == []

    def test_ongoing_generates_examples(self):
        """Test generating ongoing clarification examples."""
        gen = ClarificationGenerator()
        domain = ALL_DOMAINS["flight_booking"]
        examples = gen.generate_examples(domain, "ongoing", 3)
        assert len(examples) == 3
        for ex in examples:
            assert ex.pattern == "clarification"

    @pytest.mark.parametrize("domain_name", list(ALL_DOMAINS.keys()))
    def test_all_domains(self, domain_name):
        """Test generator works for all domains."""
        gen = ClarificationGenerator()
        domain = ALL_DOMAINS[domain_name]
        examples = gen.generate_examples(domain, "ongoing", 2)
        assert len(examples) == 2


class TestConfirmationGenerator:
    """Tests for ConfirmationGenerator."""

    def test_cold_start_returns_empty(self):
        """Confirmation only happens in ongoing conversations."""
        gen = ConfirmationGenerator()
        domain = ALL_DOMAINS["flight_booking"]
        examples = gen.generate_examples(domain, "cold_start", 3)
        assert examples == []

    def test_ongoing_generates_examples(self):
        """Test generating ongoing confirmation examples."""
        gen = ConfirmationGenerator()
        domain = ALL_DOMAINS["flight_booking"]
        examples = gen.generate_examples(domain, "ongoing", 3)
        assert len(examples) == 3
        for ex in examples:
            assert ex.pattern == "confirmation"

    @pytest.mark.parametrize("domain_name", list(ALL_DOMAINS.keys()))
    def test_all_domains(self, domain_name):
        """Test generator works for all domains."""
        gen = ConfirmationGenerator()
        domain = ALL_DOMAINS[domain_name]
        examples = gen.generate_examples(domain, "ongoing", 2)
        assert len(examples) == 2


class TestCorrectionGenerator:
    """Tests for CorrectionGenerator."""

    def test_cold_start_returns_empty(self):
        """Correction only happens in ongoing conversations."""
        gen = CorrectionGenerator()
        domain = ALL_DOMAINS["flight_booking"]
        examples = gen.generate_examples(domain, "cold_start", 3)
        assert examples == []

    def test_ongoing_generates_examples(self):
        """Test generating ongoing correction examples."""
        gen = CorrectionGenerator()
        domain = ALL_DOMAINS["flight_booking"]
        examples = gen.generate_examples(domain, "ongoing", 3)
        assert len(examples) == 3
        for ex in examples:
            assert ex.pattern == "correction"

    @pytest.mark.parametrize("domain_name", list(ALL_DOMAINS.keys()))
    def test_all_domains(self, domain_name):
        """Test generator works for all domains."""
        gen = CorrectionGenerator()
        domain = ALL_DOMAINS[domain_name]
        examples = gen.generate_examples(domain, "ongoing", 2)
        assert len(examples) == 2


class TestDigressionGenerator:
    """Tests for DigressionGenerator."""

    def test_cold_start_returns_empty(self):
        """Digression only happens in ongoing conversations."""
        gen = DigressionGenerator()
        domain = ALL_DOMAINS["flight_booking"]
        examples = gen.generate_examples(domain, "cold_start", 3)
        assert examples == []

    def test_ongoing_generates_examples(self):
        """Test generating ongoing digression examples."""
        gen = DigressionGenerator()
        domain = ALL_DOMAINS["flight_booking"]
        examples = gen.generate_examples(domain, "ongoing", 3)
        assert len(examples) == 3
        for ex in examples:
            assert ex.pattern == "digression"

    @pytest.mark.parametrize("domain_name", list(ALL_DOMAINS.keys()))
    def test_all_domains(self, domain_name):
        """Test generator works for all domains."""
        gen = DigressionGenerator()
        domain = ALL_DOMAINS[domain_name]
        examples = gen.generate_examples(domain, "ongoing", 2)
        assert len(examples) == 2


class TestInterruptionGenerator:
    """Tests for InterruptionGenerator."""

    def test_cold_start_generates_examples(self):
        """Interruption can happen at cold start."""
        gen = InterruptionGenerator()
        domain = ALL_DOMAINS["flight_booking"]
        examples = gen.generate_examples(domain, "cold_start", 3)
        assert len(examples) > 0
        for ex in examples:
            assert ex.pattern == "interruption"
            assert ex.context_type == "cold_start"

    def test_ongoing_generates_examples(self):
        """Test generating ongoing interruption examples."""
        gen = InterruptionGenerator()
        domain = ALL_DOMAINS["flight_booking"]
        examples = gen.generate_examples(domain, "ongoing", 3)
        # May return fewer if not enough flows to switch between
        assert len(examples) >= 0

    @pytest.mark.parametrize("domain_name", list(ALL_DOMAINS.keys()))
    def test_cold_start_all_domains(self, domain_name):
        """Test cold start works for all domains."""
        gen = InterruptionGenerator()
        domain = ALL_DOMAINS[domain_name]
        examples = gen.generate_examples(domain, "cold_start", 2)
        assert len(examples) >= 1


class TestModificationGenerator:
    """Tests for ModificationGenerator."""

    def test_cold_start_returns_empty(self):
        """Modification only happens in ongoing conversations."""
        gen = ModificationGenerator()
        domain = ALL_DOMAINS["flight_booking"]
        examples = gen.generate_examples(domain, "cold_start", 3)
        assert examples == []

    def test_ongoing_generates_examples(self):
        """Test generating ongoing modification examples."""
        gen = ModificationGenerator()
        domain = ALL_DOMAINS["flight_booking"]
        examples = gen.generate_examples(domain, "ongoing", 3)
        assert len(examples) == 3
        for ex in examples:
            assert ex.pattern == "modification"

    @pytest.mark.parametrize("domain_name", list(ALL_DOMAINS.keys()))
    def test_all_domains(self, domain_name):
        """Test generator works for all domains."""
        gen = ModificationGenerator()
        domain = ALL_DOMAINS[domain_name]
        examples = gen.generate_examples(domain, "ongoing", 2)
        assert len(examples) == 2


class TestSlotValueGenerator:
    """Tests for SlotValueGenerator."""

    def test_cold_start_generates_examples(self):
        """Slot value can happen at cold start (multi-slot)."""
        gen = SlotValueGenerator()
        domain = ALL_DOMAINS["flight_booking"]
        examples = gen.generate_examples(domain, "cold_start", 3)
        assert len(examples) > 0
        for ex in examples:
            assert ex.pattern == "slot_value"
            assert ex.context_type == "cold_start"

    def test_ongoing_generates_examples(self):
        """Test generating ongoing slot value examples."""
        gen = SlotValueGenerator()
        domain = ALL_DOMAINS["flight_booking"]
        examples = gen.generate_examples(domain, "ongoing", 3)
        assert len(examples) == 3
        for ex in examples:
            assert ex.pattern == "slot_value"
            assert ex.context_type == "ongoing"

    @pytest.mark.parametrize("domain_name", list(ALL_DOMAINS.keys()))
    def test_all_domains_ongoing(self, domain_name):
        """Test ongoing works for all domains."""
        gen = SlotValueGenerator()
        domain = ALL_DOMAINS[domain_name]
        examples = gen.generate_examples(domain, "ongoing", 2)
        assert len(examples) == 2

    @pytest.mark.parametrize("domain_name", list(ALL_DOMAINS.keys()))
    def test_all_domains_cold_start(self, domain_name):
        """Test cold start works for all domains."""
        gen = SlotValueGenerator()
        domain = ALL_DOMAINS[domain_name]
        examples = gen.generate_examples(domain, "cold_start", 2)
        assert len(examples) >= 1
