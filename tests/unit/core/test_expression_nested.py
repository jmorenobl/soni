import pytest

from soni.core.expression import evaluate_value


class TestValueEvaluation:
    """Tests for value evaluation and interpolation."""

    def test_substitutes_slot_value(self):
        """Should substitute {slot} with its value."""
        template = "Hello {name}"
        slots = {"name": "Alice"}
        result = evaluate_value(template, slots)
        assert result == "Hello Alice"

    def test_handles_missing_slot_gracefully(self):
        """Should handle missing slots by returning original template."""
        template = "Hello {nonexistent}"
        slots = {"name": "Alice"}
        result = evaluate_value(template, slots)
        assert result == template

    def test_preserves_non_string_values(self):
        """Should return non-string values as-is."""
        assert evaluate_value(42, {"any": "thing"}) == 42
        assert evaluate_value(True, {}) is True
