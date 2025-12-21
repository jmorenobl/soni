"""Expression evaluation for flow control.

Supports:
- Comparison: amount > 1000, status == 'approved'
- Boolean: condition1 AND condition2, condition1 OR condition2
- Existence: slot (truthy check)
- Template substitution: "Hello, {name}!"
- Branch case matching: ">1000", "<=500", "default"
"""

import operator
import re
from typing import Any

# Operators mapping - longer operators first to avoid partial matches
_OPERATORS = {
    ">=": operator.ge,
    "<=": operator.le,
    "!=": operator.ne,
    "==": operator.eq,
    ">": operator.gt,
    "<": operator.lt,
}


def evaluate_expression(expr: str, slots: dict[str, Any]) -> bool:
    """Evaluate a boolean expression against slot values.

    Args:
        expr: Expression like "age > 18 AND status == 'approved'"
        slots: Dictionary of slot_name -> value

    Returns:
        Boolean result of evaluation.

    Examples:
        >>> evaluate_expression("age > 18", {"age": 25})
        True
        >>> evaluate_expression("status == 'approved'", {"status": "approved"})
        True
        >>> evaluate_expression("items", {"items": ["a", "b"]})
        True
    """
    expr = expr.strip()

    # Handle AND/OR (case insensitive)
    and_match = re.search(r"\s+AND\s+", expr, re.IGNORECASE)
    if and_match:
        left = expr[: and_match.start()]
        right = expr[and_match.end() :]
        return evaluate_expression(left, slots) and evaluate_expression(right, slots)

    or_match = re.search(r"\s+OR\s+", expr, re.IGNORECASE)
    if or_match:
        left = expr[: or_match.start()]
        right = expr[or_match.end() :]
        return evaluate_expression(left, slots) or evaluate_expression(right, slots)

    # Handle parentheses
    if expr.startswith("(") and expr.endswith(")"):
        return evaluate_expression(expr[1:-1], slots)

    # Handle comparison operators
    for op_str, op_func in _OPERATORS.items():
        if op_str in expr:
            return _evaluate_comparison(expr, op_str, op_func, slots)

    # Simple existence/truthiness check
    slot_name = expr.strip()
    return bool(slots.get(slot_name))


def _evaluate_comparison(
    expr: str,
    op_str: str,
    op_func: Any,
    slots: dict[str, Any],
) -> bool:
    """Evaluate a single comparison expression."""
    parts = expr.split(op_str, 1)
    if len(parts) != 2:
        return False

    left_expr = parts[0].strip()
    right_expr = parts[1].strip()

    left_val = slots.get(left_expr)
    right_val = _parse_literal(right_expr, slots)

    # Equality operators are None-safe
    if op_str in ("==", "!="):
        return bool(op_func(left_val, right_val))

    # Ordering operators require non-None left value
    if left_val is None:
        return False

    # Numeric comparison
    left_num = _to_number(left_val)
    right_num = _to_number(right_val)

    if left_num is not None and right_num is not None:
        return bool(op_func(left_num, right_num))

    # String comparison fallback
    if isinstance(left_val, str) and isinstance(right_val, str):
        return bool(op_func(left_val, right_val))

    return False


def _to_number(val: Any) -> float | int | None:
    """Try to convert value to number."""
    if isinstance(val, (int, float)):
        return val
    if isinstance(val, str):
        try:
            return float(val) if "." in val else int(val)
        except ValueError:
            return None
    return None


def _parse_literal(expr: str, slots: dict[str, Any]) -> Any:
    """Parse a value expression (literal or slot reference)."""
    expr = expr.strip()

    # String literal (quoted)
    if (expr.startswith("'") and expr.endswith("'")) or (
        expr.startswith('"') and expr.endswith('"')
    ):
        return expr[1:-1]

    # Numeric literal
    num = _to_number(expr)
    if num is not None:
        return num

    # Boolean literals
    if expr.lower() == "true":
        return True
    if expr.lower() == "false":
        return False

    # None literal
    if expr.lower() in ("none", "null"):
        return None

    # Slot reference
    return slots.get(expr)


def evaluate_value(value_expr: str | Any, slots: dict[str, Any]) -> Any:
    """Evaluate value expression with template substitution.

    Args:
        value_expr: Value or template like "Hello, {name}!"
        slots: Dictionary of slot_name -> value

    Returns:
        Evaluated value with templates replaced.

    Examples:
        >>> evaluate_value("Hello, {name}!", {"name": "Alice"})
        "Hello, Alice!"
        >>> evaluate_value(42, {})
        42
    """
    if not isinstance(value_expr, str):
        return value_expr

    if "{" not in value_expr:
        return value_expr

    try:
        return value_expr.format(**slots)
    except (KeyError, ValueError):
        # Return original if substitution fails
        return value_expr


def matches(value: Any, pattern: str) -> bool:
    """Check if a value matches a branch case pattern.

    Patterns:
        - ">N", ">=N", "<N", "<=N": Numeric comparison
        - "==value", "!=value": Equality
        - "true", "false": Boolean match
        - "default": Always matches (handled by caller)
        - "literal": Exact string match

    Args:
        value: The slot value to check.
        pattern: The case pattern (e.g., ">1000", "approved").

    Returns:
        True if value matches pattern.

    Examples:
        >>> matches(500, ">1000")
        False
        >>> matches(1500, ">1000")
        True
        >>> matches("approved", "approved")
        True
    """
    pattern = pattern.strip()

    # Comparison operators
    for op_str, op_func in _OPERATORS.items():
        if pattern.startswith(op_str):
            threshold_str = pattern[len(op_str) :].strip()
            threshold = _to_number(threshold_str)
            val_num = _to_number(value)

            if threshold is not None and val_num is not None:
                return bool(op_func(val_num, threshold))

            # String comparison for equality operators
            if op_str in ("==", "!="):
                return bool(op_func(str(value), threshold_str))

            return False

    # Boolean pattern
    if pattern.lower() == "true":
        return bool(value) is True
    if pattern.lower() == "false":
        return bool(value) is False

    # Exact string match
    return str(value) == pattern
