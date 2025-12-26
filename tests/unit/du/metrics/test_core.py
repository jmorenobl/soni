import pytest

from soni.du.metrics.core import MetricScore, compare_values, normalize_value


class TestMetricCore:
    """Tests for core metric utilities."""

    def test_metric_score_repr(self):
        """Should have a clean string representation."""
        score = MetricScore(type_score=1.0, field_score=0.5, value_score=0.0, total=0.5)
        assert "Score(type=1.00, field=0.50, value=0.00, total=0.50)" in repr(score)

    def test_normalize_value(self):
        """Should lowercase, strip and handle None."""
        assert normalize_value("  TEST  ") == "test"
        assert normalize_value(None) == ""
        assert normalize_value(123) == "123"

    def test_compare_values_exact(self):
        """Should return 1.0 for exact matches."""
        assert compare_values("test", "test") == 1.0
        assert compare_values("test", " TEST ") == 1.0
        assert compare_values(None, "") == 1.0

    def test_compare_values_partial(self):
        """Should return 0.5 for partial matches (overlap)."""
        assert compare_values("apple", "apple pie") == 0.5
        assert compare_values("apple pie", "apple") == 0.5
        assert compare_values("test", "testing") == 0.5

    def test_compare_values_mismatch(self):
        """Should return 0.0 for distinct values."""
        assert compare_values("apple", "orange") == 0.0
        assert compare_values("123", "456") == 0.0
