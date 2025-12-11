"""Unit tests for DSPy metrics"""

import dspy
import pytest

from soni.du.metrics import intent_accuracy_metric
from soni.du.models import MessageType, NLUOutput, SlotValue


def test_intent_accuracy_perfect_match():
    """Test metric with perfect message_type, command and slot match"""
    # Arrange
    example = dspy.Example(
        result=NLUOutput(
            message_type=MessageType.SLOT_VALUE,
            command="book_flight",
            slots=[SlotValue(name="destination", value="Paris", confidence=0.9)],
            confidence=0.9,
        )
    )
    prediction = dspy.Prediction(
        result=NLUOutput(
            message_type=MessageType.SLOT_VALUE,
            command="book_flight",
            slots=[SlotValue(name="destination", value="Paris", confidence=0.9)],
            confidence=0.9,
        )
    )

    # Act
    score = intent_accuracy_metric(example, prediction)

    # Assert
    assert score == 1.0


def test_intent_accuracy_intent_match_only():
    """Test metric with message_type and command match but slot mismatch"""
    # Arrange
    example = dspy.Example(
        result=NLUOutput(
            message_type=MessageType.SLOT_VALUE,
            command="book_flight",
            slots=[SlotValue(name="destination", value="Paris", confidence=0.9)],
            confidence=0.9,
        )
    )
    prediction = dspy.Prediction(
        result=NLUOutput(
            message_type=MessageType.SLOT_VALUE,
            command="book_flight",
            slots=[SlotValue(name="destination", value="London", confidence=0.9)],
            confidence=0.9,
        )
    )

    # Act
    score = intent_accuracy_metric(example, prediction)

    # Assert - Should get 40% (message_type) + 30% (command) + 0% (slot mismatch) = 0.7
    assert score == pytest.approx(0.7, abs=0.01)


def test_intent_accuracy_slot_match_only():
    """Test metric with slot match but command mismatch"""
    # Arrange
    example = dspy.Example(
        result=NLUOutput(
            message_type=MessageType.SLOT_VALUE,
            command="book_flight",
            slots=[SlotValue(name="destination", value="Paris", confidence=0.9)],
            confidence=0.9,
        )
    )
    prediction = dspy.Prediction(
        result=NLUOutput(
            message_type=MessageType.SLOT_VALUE,
            command="search_flights",
            slots=[SlotValue(name="destination", value="Paris", confidence=0.9)],
            confidence=0.9,
        )
    )

    # Act
    score = intent_accuracy_metric(example, prediction)

    # Assert - Should get 40% (message_type) + 0% (command mismatch) + 30% (slot match) = 0.7
    assert score == pytest.approx(0.7, abs=0.01)


def test_intent_accuracy_no_match():
    """Test metric with no matches"""
    # Arrange
    example = dspy.Example(
        result=NLUOutput(
            message_type=MessageType.SLOT_VALUE,
            command="book_flight",
            slots=[SlotValue(name="destination", value="Paris", confidence=0.9)],
            confidence=0.9,
        )
    )
    prediction = dspy.Prediction(
        result=NLUOutput(
            message_type=MessageType.CANCELLATION,
            command="cancel_booking",
            slots=[],
            confidence=0.9,
        )
    )

    # Act
    score = intent_accuracy_metric(example, prediction)

    # Assert
    assert score == 0.0


def test_intent_accuracy_case_insensitive():
    """Test metric handles case-insensitive command matching"""
    # Arrange
    example = dspy.Example(
        result=NLUOutput(
            message_type=MessageType.SLOT_VALUE,
            command="Book_Flight",
            slots=[SlotValue(name="destination", value="Paris", confidence=0.9)],
            confidence=0.9,
        )
    )
    prediction = dspy.Prediction(
        result=NLUOutput(
            message_type=MessageType.SLOT_VALUE,
            command="book_flight",
            slots=[SlotValue(name="destination", value="Paris", confidence=0.9)],
            confidence=0.9,
        )
    )

    # Act
    score = intent_accuracy_metric(example, prediction)

    # Assert - Command should match (case-insensitive)
    assert score == pytest.approx(1.0, abs=0.01)


def test_intent_accuracy_fuzzy_slot_matching():
    """Test metric handles fuzzy slot value matching"""
    # Arrange
    example = dspy.Example(
        result=NLUOutput(
            message_type=MessageType.SLOT_VALUE,
            command="book_flight",
            slots=[SlotValue(name="destination", value="Paris", confidence=0.9)],
            confidence=0.9,
        )
    )
    prediction = dspy.Prediction(
        result=NLUOutput(
            message_type=MessageType.SLOT_VALUE,
            command="book_flight",
            slots=[SlotValue(name="destination", value="paris, france", confidence=0.9)],
            confidence=0.9,
        )
    )

    # Act
    score = intent_accuracy_metric(example, prediction)

    # Assert - Should match because "paris" is in "paris, france" (fuzzy matching)
    assert score == pytest.approx(1.0, abs=0.01)


def test_intent_accuracy_empty_slots():
    """Test metric with empty slots"""
    # Arrange
    example = dspy.Example(
        result=NLUOutput(
            message_type=MessageType.DIGRESSION,
            command=None,
            slots=[],
            confidence=0.9,
        )
    )
    prediction = dspy.Prediction(
        result=NLUOutput(
            message_type=MessageType.DIGRESSION,
            command=None,
            slots=[],
            confidence=0.9,
        )
    )

    # Act
    score = intent_accuracy_metric(example, prediction)

    # Assert - Should get full score for message_type and command match
    assert score == pytest.approx(1.0, abs=0.01)


def test_intent_accuracy_invalid_json():
    """Test metric handles invalid result gracefully"""
    # Arrange
    example = dspy.Example(
        result=NLUOutput(
            message_type=MessageType.SLOT_VALUE,
            command="book_flight",
            slots=[SlotValue(name="destination", value="Paris", confidence=0.9)],
            confidence=0.9,
        )
    )
    # Prediction with invalid result (dict that can't be converted to NLUOutput)
    prediction = dspy.Prediction(result={"invalid": "data"})

    # Act
    score = intent_accuracy_metric(example, prediction)

    # Assert - Should return 0.0 when result can't be extracted
    assert score == 0.0


def test_intent_accuracy_missing_attributes():
    """Test metric handles missing result field gracefully"""
    # Arrange
    example = dspy.Example(
        result=NLUOutput(
            message_type=MessageType.SLOT_VALUE,
            command="book_flight",
            slots=[SlotValue(name="destination", value="Paris", confidence=0.9)],
            confidence=0.9,
        )
    )
    prediction = dspy.Prediction()
    # Missing result field

    # Act
    score = intent_accuracy_metric(example, prediction)

    # Assert - Should return 0.0 when result is missing
    assert score == 0.0


def test_intent_accuracy_empty_strings():
    """Test metric handles None commands"""
    # Arrange
    example = dspy.Example(
        result=NLUOutput(
            message_type=MessageType.SLOT_VALUE,
            command=None,
            slots=[],
            confidence=0.9,
        )
    )
    prediction = dspy.Prediction(
        result=NLUOutput(
            message_type=MessageType.SLOT_VALUE,
            command=None,
            slots=[],
            confidence=0.9,
        )
    )

    # Act
    score = intent_accuracy_metric(example, prediction)

    # Assert - None commands should match (both converted to empty string)
    assert score == pytest.approx(1.0, abs=0.01)
