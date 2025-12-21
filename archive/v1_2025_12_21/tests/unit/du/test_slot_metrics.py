"""Tests for slot extraction metrics."""

from unittest.mock import Mock

import pytest

from soni.du.metrics import create_slot_extraction_metric, normalize_value


class TestSlotExtractionMetric:
    """Tests for slot extraction metric function."""

    @pytest.fixture
    def metric(self):
        return create_slot_extraction_metric()

    def test_normalize_value(self):
        """GIVEN value WHEN normalized THEN lowercased and stripped."""
        assert normalize_value("  Hello  ") == "hello"
        assert normalize_value(None) == ""
        assert normalize_value(123) == "123"

    def test_perfect_match(self, metric):
        """GIVEN exact match WHEN scored THEN returns 1.0."""
        expected = [{"slot": "amount", "value": "100"}]

        example = Mock()
        example.result.extracted_slots = expected

        prediction = Mock()
        prediction.extracted_slots = expected

        assert metric(example, prediction) == 1.0

    def test_partial_match(self, metric):
        """GIVEN partial match WHEN scored THEN returns overlap ratio."""
        expected = [
            {"slot": "amount", "value": "100"},
            {"slot": "currency", "value": "USD"},
        ]

        example = Mock()
        example.result.extracted_slots = expected

        # Missing currency
        prediction = Mock()
        prediction.extracted_slots = [{"slot": "amount", "value": "100"}]

        # 1 correct / 2 expected = 0.5
        assert metric(example, prediction) == 0.5

    def test_empty_match(self, metric):
        """GIVEN both empty WHEN scored THEN returns 1.0."""
        example = Mock()
        example.result.extracted_slots = []

        prediction = Mock()
        prediction.extracted_slots = []

        assert metric(example, prediction) == 1.0

    def test_hallucination_penalty(self, metric):
        """GIVEN hallucinated extra slot WHEN scored THEN penalized."""
        expected = [{"slot": "amount", "value": "100"}]

        example = Mock()
        example.result.extracted_slots = expected

        # Extra slot
        prediction = Mock()
        prediction.extracted_slots = [
            {"slot": "amount", "value": "100"},
            {"slot": "currency", "value": "USD"},
        ]

        # 1 correct / 2 actual = 0.5 (denominator is max len)
        assert metric(example, prediction) == 0.5

    def test_wrapped_prediction_result(self, metric):
        """GIVEN prediction wrapped in result object WHEN scored THEN handles it."""
        expected = [{"slot": "a", "value": "1"}]
        example = Mock()
        example.result.extracted_slots = expected

        # Prediction wrapper pattern
        # Use spec to ensure 'extracted_slots' doesn't exist on top level
        prediction = Mock(spec=["result"])
        prediction.result = Mock()
        prediction.result.extracted_slots = expected

        assert metric(example, prediction) == 1.0
