from unittest.mock import MagicMock

import pytest

from soni.du.metrics.adapters import adapt_metric_for_gepa, create_slot_extraction_metric


class TestMetricAdapters:
    """Tests for metric adapters."""

    def test_adapt_metric_for_gepa(self):
        """Should wrap metric and return float."""
        mock_metric = MagicMock(return_value=1)
        gepa_metric = adapt_metric_for_gepa(mock_metric)

        result = gepa_metric(MagicMock(), MagicMock(), trace="trace")
        assert result == 1.0
        assert isinstance(result, float)
        mock_metric.assert_called_once()

    def test_slot_extraction_metric_success(self):
        """Should score slot extraction correctly."""
        metric_fn = create_slot_extraction_metric()

        example = MagicMock()
        example.result.extracted_slots = [
            {"slot": "amount", "value": "100"},
            {"slot": "currency", "value": "USD"},
        ]

        # Perfect match
        pred = MagicMock()
        pred.extracted_slots = [
            {"slot": "amount", "value": "100"},
            {"slot": "currency", "value": "USD"},
        ]
        assert metric_fn(example, pred) == 1.0

        # Partial match (1 correct out of 2 expected)
        pred.extracted_slots = [{"slot": "amount", "value": "100"}]
        assert metric_fn(example, pred) == 0.5

        # Hallucination (1 correct, 1 wrong)
        pred.extracted_slots = [
            {"slot": "amount", "value": "100"},
            {"slot": "other", "value": "val"},
        ]
        # Max(2, 2) = 2. Correct = 1. Score = 0.5
        assert metric_fn(example, pred) == 0.5

    def test_slot_extraction_metric_empty(self):
        """Should handle empty cases."""
        metric_fn = create_slot_extraction_metric()

        example = MagicMock()
        example.result.extracted_slots = []

        pred = MagicMock()
        pred.extracted_slots = []

        assert metric_fn(example, pred) == 1.0

        # Hallucination when nothing expected
        pred.extracted_slots = [{"slot": "a", "value": "b"}]
        assert metric_fn(example, pred) == 0.0

    def test_slot_extraction_metric_error_handling(self):
        """Should return 0.0 on malformed input."""
        metric_fn = create_slot_extraction_metric()
        assert metric_fn(None, None) == 0.0

        example = MagicMock()
        example.result = None
        assert metric_fn(example, MagicMock()) == 0.0
