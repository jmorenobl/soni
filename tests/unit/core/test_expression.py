"""Unit tests for expression evaluator."""

import pytest

from soni.core.expression import evaluate_condition


class TestSimpleConditions:
    """Tests for simple comparison conditions."""

    def test_equality_string(self):
        assert evaluate_condition("status == 'approved'", {"status": "approved"}) is True
        assert evaluate_condition("status == 'approved'", {"status": "pending"}) is False

    def test_equality_with_double_quotes(self):
        assert evaluate_condition('status == "approved"', {"status": "approved"}) is True

    def test_inequality(self):
        assert evaluate_condition("status != 'rejected'", {"status": "approved"}) is True
        assert evaluate_condition("status != 'approved'", {"status": "approved"}) is False

    def test_greater_than(self):
        assert evaluate_condition("age > 18", {"age": 25}) is True
        assert evaluate_condition("age > 18", {"age": 18}) is False
        assert evaluate_condition("age > 18", {"age": 15}) is False

    def test_greater_than_or_equal(self):
        assert evaluate_condition("age >= 18", {"age": 18}) is True
        assert evaluate_condition("age >= 18", {"age": 25}) is True
        assert evaluate_condition("age >= 18", {"age": 17}) is False

    def test_less_than(self):
        assert evaluate_condition("amount < 5000", {"amount": 1000}) is True
        assert evaluate_condition("amount < 5000", {"amount": 5000}) is False

    def test_less_than_or_equal(self):
        assert evaluate_condition("amount <= 5000", {"amount": 5000}) is True
        assert evaluate_condition("amount <= 5000", {"amount": 5001}) is False


class TestExistenceCheck:
    """Tests for slot existence/truthiness."""

    def test_slot_exists_with_value(self):
        assert evaluate_condition("items", {"items": ["a", "b"]}) is True

    def test_slot_exists_empty_list(self):
        assert evaluate_condition("items", {"items": []}) is False

    def test_slot_not_exists(self):
        assert evaluate_condition("missing_slot", {}) is False

    def test_slot_none_value(self):
        assert evaluate_condition("slot", {"slot": None}) is False

    def test_slot_zero_value(self):
        assert evaluate_condition("count", {"count": 0}) is False

    def test_slot_truthy_string(self):
        assert evaluate_condition("name", {"name": "John"}) is True


class TestBooleanOperators:
    """Tests for AND/OR operators."""

    def test_and_both_true(self):
        slots = {"age": 25, "status": "approved"}
        assert evaluate_condition("age > 18 AND status == 'approved'", slots) is True

    def test_and_one_false(self):
        slots = {"age": 15, "status": "approved"}
        assert evaluate_condition("age > 18 AND status == 'approved'", slots) is False

    def test_or_one_true(self):
        slots = {"age": 15, "status": "approved"}
        assert evaluate_condition("age > 18 OR status == 'approved'", slots) is True

    def test_or_both_false(self):
        slots = {"age": 15, "status": "rejected"}
        assert evaluate_condition("age > 18 OR status == 'approved'", slots) is False

    def test_complex_and_or(self):
        slots = {"age": 25, "status": "pending", "vip": True}
        # age > 18 AND (status == 'approved' OR vip)
        assert evaluate_condition("age > 18 AND vip", slots) is True


class TestParentheses:
    """Tests for parentheses grouping."""

    def test_simple_parens(self):
        assert evaluate_condition("(age > 18)", {"age": 25}) is True

    def test_nested_parens(self):
        slots = {"age": 25, "status": "approved"}
        assert evaluate_condition("(age > 18) AND (status == 'approved')", slots) is True


class TestEdgeCases:
    """Edge case tests."""

    def test_string_numeric_comparison(self):
        # String slot compared to numeric literal
        assert evaluate_condition("age > 18", {"age": "25"}) is True

    def test_float_comparison(self):
        assert evaluate_condition("price < 99.99", {"price": 50.0}) is True

    def test_negative_numbers(self):
        assert evaluate_condition("balance > -100", {"balance": 0}) is True

    def test_case_insensitive_boolean_operators(self):
        slots = {"a": True, "b": True}
        assert evaluate_condition("a and b", slots) is True
        assert evaluate_condition("a or b", slots) is True

    def test_whitespace_handling(self):
        assert evaluate_condition("  age  >  18  ", {"age": 25}) is True
        assert evaluate_condition("status=='approved'", {"status": "approved"}) is True

    def test_missing_slot_returns_false(self):
        assert evaluate_condition("missing > 10", {}) is False

    def test_boolean_literal(self):
        assert evaluate_condition("active == true", {"active": True}) is True
        assert evaluate_condition("active == false", {"active": False}) is True
