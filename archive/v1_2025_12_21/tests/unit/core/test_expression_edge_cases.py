import pytest

from soni.core.expression import evaluate_condition


class TestExpressionEdgeCases:
    def test_none_equality_missing_slot(self):
        """Test that missing slot equals None."""
        assert evaluate_condition("missing_slot == None", {}) is True
        assert evaluate_condition("missing_slot == null", {}) is True

    def test_none_equality_explicit_none(self):
        """Test that explicit None value equals None."""
        assert evaluate_condition("slot == None", {"slot": None}) is True

    def test_neq_missing_slot(self):
        """Test that missing slot is not equal to a string."""
        # If missing is None, None != "foo" is True
        assert evaluate_condition("missing_slot != 'foo'", {}) is True

    def test_safe_numeric_comparison_mismatch(self):
        """Test that comparing string to number via numeric operator returns False."""
        # Current implementation does string compare ("abc" > "10" is True)
        # We want strict typing: string vs number with numeric op should be False
        assert evaluate_condition("var > 10", {"var": "abc"}) is False
        assert evaluate_condition("var < 100", {"var": "abc"}) is False

    def test_mixed_numeric_types(self):
        """Test valid numeric comparison between float and int."""
        assert evaluate_condition("val > 10.5", {"val": 11}) is True
        assert evaluate_condition("val > 10", {"val": 10.5}) is True
