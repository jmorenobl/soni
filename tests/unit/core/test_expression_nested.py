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

    def test_multiple_substitutions(self):
        """Should handle multiple placeholders in one template."""
        template = "Hello {name}, your balance is {balance}"
        slots = {"name": "Alice", "balance": 1000}
        result = evaluate_value(template, slots)
        assert result == "Hello Alice, your balance is 1000"

    def test_handles_complex_types_in_placeholders(self):
        """Should handle non-string types in placeholders."""
        template = "Result: {data}"
        slots = {"data": [1, 2, 3]}
        result = evaluate_value(template, slots)
        assert result == "Result: [1, 2, 3]"

    def test_no_placeholder_returns_original(self):
        """Should return original string if no placeholders."""
        template = "Plain text"
        assert evaluate_value(template, {}) == template
