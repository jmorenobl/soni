"""Unit tests for DSPy metrics"""

import json

import dspy
import pytest

from soni.du.metrics import intent_accuracy_metric


def test_intent_accuracy_perfect_match():
    """Test metric with perfect intent and slot match"""
    # Arrange
    example = dspy.Example(
        structured_command="book_flight",
        extracted_slots='{"destination": "Paris"}',
    )
    prediction = dspy.Prediction(
        structured_command="book_flight",
        extracted_slots='{"destination": "Paris"}',
    )

    # Act
    score = intent_accuracy_metric(example, prediction)

    # Assert
    assert score == 1.0


def test_intent_accuracy_intent_match_only():
    """Test metric with intent match but slot mismatch"""
    # Arrange
    example = dspy.Example(
        structured_command="book_flight",
        extracted_slots='{"destination": "Paris"}',
    )
    prediction = dspy.Prediction(
        structured_command="book_flight",
        extracted_slots='{"destination": "London"}',
    )

    # Act
    score = intent_accuracy_metric(example, prediction)

    # Assert - Should get 70% (intent match) + 0% (slot mismatch) = 0.7
    assert score == pytest.approx(0.7, abs=0.01)


def test_intent_accuracy_slot_match_only():
    """Test metric with slot match but intent mismatch"""
    # Arrange
    example = dspy.Example(
        structured_command="book_flight",
        extracted_slots='{"destination": "Paris"}',
    )
    prediction = dspy.Prediction(
        structured_command="search_flights",
        extracted_slots='{"destination": "Paris"}',
    )

    # Act
    score = intent_accuracy_metric(example, prediction)

    # Assert - Should get 0% (intent mismatch) + 30% (slot match) = 0.3
    assert score == pytest.approx(0.3, abs=0.01)


def test_intent_accuracy_no_match():
    """Test metric with no matches"""
    # Arrange
    example = dspy.Example(
        structured_command="book_flight",
        extracted_slots='{"destination": "Paris"}',
    )
    prediction = dspy.Prediction(
        structured_command="cancel",
        extracted_slots='{"action": "cancel"}',
    )

    # Act
    score = intent_accuracy_metric(example, prediction)

    # Assert
    assert score == 0.0


def test_intent_accuracy_case_insensitive():
    """Test metric handles case-insensitive intent matching"""
    # Arrange
    example = dspy.Example(
        structured_command="Book_Flight",
        extracted_slots='{"destination": "Paris"}',
    )
    prediction = dspy.Prediction(
        structured_command="book_flight",
        extracted_slots='{"destination": "Paris"}',
    )

    # Act
    score = intent_accuracy_metric(example, prediction)

    # Assert - Intent should match (case-insensitive)
    assert score == pytest.approx(1.0, abs=0.01)


def test_intent_accuracy_fuzzy_slot_matching():
    """Test metric handles fuzzy slot value matching"""
    # Arrange
    example = dspy.Example(
        structured_command="book_flight",
        extracted_slots='{"destination": "Paris"}',
    )
    prediction = dspy.Prediction(
        structured_command="book_flight",
        extracted_slots='{"destination": "paris, france"}',
    )

    # Act
    score = intent_accuracy_metric(example, prediction)

    # Assert - Should match because "paris" is in "paris, france"
    assert score == pytest.approx(1.0, abs=0.01)


def test_intent_accuracy_empty_slots():
    """Test metric with empty slots"""
    # Arrange
    example = dspy.Example(
        structured_command="help",
        extracted_slots="{}",
    )
    prediction = dspy.Prediction(
        structured_command="help",
        extracted_slots="{}",
    )

    # Act
    score = intent_accuracy_metric(example, prediction)

    # Assert - Should get full score for intent match
    assert score == pytest.approx(1.0, abs=0.01)


def test_intent_accuracy_invalid_json():
    """Test metric handles invalid JSON gracefully"""
    # Arrange
    example = dspy.Example(
        structured_command="book_flight",
        extracted_slots='{"destination": "Paris"}',
    )
    prediction = dspy.Prediction(
        structured_command="book_flight",
        extracted_slots="invalid json",
    )

    # Act
    score = intent_accuracy_metric(example, prediction)

    # Assert - Should get 70% for intent match, 0% for slots (invalid JSON)
    assert score == pytest.approx(0.7, abs=0.01)


def test_intent_accuracy_missing_attributes():
    """Test metric handles missing attributes gracefully"""
    # Arrange
    example = dspy.Example(
        structured_command="book_flight",
        extracted_slots='{"destination": "Paris"}',
    )
    prediction = dspy.Prediction()
    # Missing structured_command and extracted_slots

    # Act
    score = intent_accuracy_metric(example, prediction)

    # Assert - Should return 0.0 for any error
    assert score == 0.0


def test_intent_accuracy_empty_strings():
    """Test metric handles empty strings"""
    # Arrange
    example = dspy.Example(
        structured_command="",
        extracted_slots="{}",
    )
    prediction = dspy.Prediction(
        structured_command="",
        extracted_slots="{}",
    )

    # Act
    score = intent_accuracy_metric(example, prediction)

    # Assert - Empty strings should match
    assert score == pytest.approx(1.0, abs=0.01)
