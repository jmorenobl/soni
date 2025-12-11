"""Unit tests for pattern generators."""

import dspy
import pytest

from soni.dataset.domains.flight_booking import FLIGHT_BOOKING
from soni.dataset.domains.hotel_booking import HOTEL_BOOKING
from soni.dataset.patterns.cancellation import CancellationGenerator
from soni.dataset.patterns.clarification import ClarificationGenerator
from soni.dataset.patterns.confirmation import ConfirmationGenerator
from soni.dataset.patterns.continuation import ContinuationGenerator
from soni.dataset.patterns.correction import CorrectionGenerator
from soni.dataset.patterns.digression import DigressionGenerator
from soni.dataset.patterns.interruption import InterruptionGenerator
from soni.dataset.patterns.modification import ModificationGenerator
from soni.dataset.patterns.slot_value import SlotValueGenerator
from soni.du.models import MessageType


def test_slot_value_generator_message_type():
    """Test SlotValueGenerator returns correct message_type."""
    # Arrange
    generator = SlotValueGenerator()

    # Assert
    assert generator.message_type == MessageType.SLOT_VALUE


def test_slot_value_generator_cold_start_flight_booking():
    """Test generating cold start examples for flight booking."""
    # Arrange
    generator = SlotValueGenerator()

    # Act
    examples = generator.generate_examples(
        domain_config=FLIGHT_BOOKING,
        context_type="cold_start",
        count=3,
    )

    # Assert
    assert len(examples) == 3
    assert all(ex.context_type == "cold_start" for ex in examples)
    assert all(ex.domain == "flight_booking" for ex in examples)
    assert all(ex.pattern == "slot_value" for ex in examples)
    # Cold start should use INTERRUPTION (starting new flow)
    assert all(ex.expected_output.message_type == MessageType.INTERRUPTION for ex in examples)


def test_slot_value_generator_ongoing_flight_booking():
    """Test generating ongoing examples for flight booking."""
    # Arrange
    generator = SlotValueGenerator()

    # Act
    examples = generator.generate_examples(
        domain_config=FLIGHT_BOOKING,
        context_type="ongoing",
        count=3,
    )

    # Assert
    assert len(examples) == 3
    assert all(ex.context_type == "ongoing" for ex in examples)
    assert all(ex.domain == "flight_booking" for ex in examples)
    # Ongoing should use SLOT_VALUE
    assert all(ex.expected_output.message_type == MessageType.SLOT_VALUE for ex in examples)
    # Ongoing examples should have history
    assert all(len(ex.conversation_context.history.messages) > 0 for ex in examples)


def test_slot_value_generator_respects_count():
    """Test generator respects count parameter."""
    # Arrange
    generator = SlotValueGenerator()

    # Act
    examples_2 = generator.generate_examples(FLIGHT_BOOKING, "cold_start", count=2)
    examples_5 = generator.generate_examples(FLIGHT_BOOKING, "cold_start", count=5)

    # Assert
    assert len(examples_2) <= 2  # May have fewer if not enough variations
    assert len(examples_5) <= 5


def test_slot_value_generator_works_with_all_domains():
    """Test generator works with all domains."""
    # Arrange
    generator = SlotValueGenerator()
    from soni.dataset.domains import ALL_DOMAINS

    # Act & Assert - should not raise
    for domain_name, domain_config in ALL_DOMAINS.items():
        examples_cold = generator.generate_examples(domain_config, "cold_start", count=1)
        examples_ongoing = generator.generate_examples(domain_config, "ongoing", count=1)

        assert len(examples_cold) >= 1, f"No cold_start examples for {domain_name}"
        assert len(examples_ongoing) >= 1, f"No ongoing examples for {domain_name}"


def test_slot_value_examples_have_required_fields():
    """Test generated examples have all required fields."""
    # Arrange
    generator = SlotValueGenerator()

    # Act
    examples = generator.generate_examples(FLIGHT_BOOKING, "cold_start", count=1)
    example = examples[0]

    # Assert
    assert example.user_message
    assert example.conversation_context is not None
    assert example.expected_output is not None
    assert example.domain == "flight_booking"
    assert example.pattern == "slot_value"
    assert example.expected_output.command
    assert isinstance(example.expected_output.slots, list)
    assert 0.0 <= example.expected_output.confidence <= 1.0


def test_slot_value_examples_convert_to_dspy_example():
    """Test examples can be converted to dspy.Example."""
    # Arrange
    generator = SlotValueGenerator()
    templates = generator.generate_examples(FLIGHT_BOOKING, "cold_start", count=1)
    template = templates[0]

    # Act
    example = template.to_dspy_example(FLIGHT_BOOKING)

    # Assert
    assert isinstance(example, dspy.Example)
    assert hasattr(example, "user_message")
    assert hasattr(example, "history")
    assert hasattr(example, "context")
    assert hasattr(example, "result")


# CORRECTION and MODIFICATION Tests


def test_correction_generator_message_type():
    """Test CorrectionGenerator returns correct message_type."""
    assert CorrectionGenerator().message_type == MessageType.CORRECTION


def test_correction_returns_empty_for_cold_start():
    """Test corrections only work in ongoing context."""
    generator = CorrectionGenerator()
    examples = generator.generate_examples(FLIGHT_BOOKING, "cold_start", count=3)
    assert len(examples) == 0


def test_correction_generates_ongoing_examples():
    """Test correction generates ongoing examples."""
    generator = CorrectionGenerator()
    examples = generator.generate_examples(FLIGHT_BOOKING, "ongoing", count=2)
    assert len(examples) >= 1
    assert all(ex.expected_output.message_type == MessageType.CORRECTION for ex in examples)


def test_modification_generator_message_type():
    """Test ModificationGenerator returns correct message_type."""
    assert ModificationGenerator().message_type == MessageType.MODIFICATION


def test_modification_returns_empty_for_cold_start():
    """Test modifications only work in ongoing context."""
    generator = ModificationGenerator()
    examples = generator.generate_examples(FLIGHT_BOOKING, "cold_start", count=3)
    assert len(examples) == 0


def test_modification_generates_ongoing_examples():
    """Test modification generates ongoing examples."""
    generator = ModificationGenerator()
    examples = generator.generate_examples(FLIGHT_BOOKING, "ongoing", count=2)
    assert len(examples) >= 1
    assert all(ex.expected_output.message_type == MessageType.MODIFICATION for ex in examples)


# Flow Control Tests


def test_interruption_cold_start_and_ongoing():
    """Test INTERRUPTION works in both contexts."""
    gen = InterruptionGenerator()
    cold = gen.generate_examples(FLIGHT_BOOKING, "cold_start", 1)
    ongoing = gen.generate_examples(FLIGHT_BOOKING, "ongoing", 1)
    assert len(cold) >= 1
    assert len(ongoing) >= 1


def test_cancellation_ongoing_only():
    """Test CANCELLATION only in ongoing."""
    gen = CancellationGenerator()
    cold = gen.generate_examples(FLIGHT_BOOKING, "cold_start", 3)
    ongoing = gen.generate_examples(FLIGHT_BOOKING, "ongoing", 3)
    assert len(cold) == 0  # No cold start
    assert len(ongoing) >= 1


def test_continuation_ongoing_only():
    """Test CONTINUATION only in ongoing."""
    gen = ContinuationGenerator()
    cold = gen.generate_examples(FLIGHT_BOOKING, "cold_start", 3)
    ongoing = gen.generate_examples(FLIGHT_BOOKING, "ongoing", 3)
    assert len(cold) == 0
    assert len(ongoing) >= 1


# Question Patterns Tests


def test_all_question_patterns_ongoing_only():
    """Test all question patterns work only in ongoing."""
    patterns = [
        DigressionGenerator(),
        ClarificationGenerator(),
        ConfirmationGenerator(),
    ]

    for gen in patterns:
        cold = gen.generate_examples(FLIGHT_BOOKING, "cold_start", 3)
        ongoing = gen.generate_examples(FLIGHT_BOOKING, "ongoing", 3)
        assert len(cold) == 0, f"{gen.message_type} should not work in cold_start"
        assert len(ongoing) >= 1, f"{gen.message_type} should work in ongoing"


def test_confirmation_positive_and_negative():
    """Test confirmation includes both positive and negative examples."""
    gen = ConfirmationGenerator()
    examples = gen.generate_examples(FLIGHT_BOOKING, "ongoing", 5)

    # Should have mix of positive and negative
    positive = [
        ex
        for ex in examples
        if "yes" in ex.user_message.lower() or "correct" in ex.user_message.lower()
    ]
    negative = [ex for ex in examples if "no" in ex.user_message.lower()]

    assert len(positive) >= 1
    assert len(negative) >= 1
