"""Condition expression evaluator for flow control.

Supports:
- Comparison: age > 18, status == 'approved', amount < 5000
- Equality: slot == "value", slot != "value"
- Existence: slot (truthy check)
- Boolean: condition1 AND condition2, condition1 OR condition2
- Grouping: (age > 18) AND (status == 'approved')
"""

import logging
import operator
import re
from typing import Any

logger = logging.getLogger(__name__)

# Operators mapping - longer operators first to avoid partial matches
OPERATORS = {
    ">=": operator.ge,
    "<=": operator.le,
    "!=": operator.ne,
    "==": operator.eq,
    ">": operator.gt,
    "<": operator.lt,
}


def evaluate_condition(condition: str, slots: dict[str, Any]) -> bool:
    """Evaluate a condition expression against slot values.

    Args:
        condition: Expression like "age > 18 AND status == 'approved'"
        slots: Dictionary of slot_name -> value

    Returns:
        Boolean result of evaluation.

    Examples:
        >>> evaluate_condition("age > 18", {"age": 25})
        True
        >>> evaluate_condition("status == 'approved'", {"status": "approved"})
        True
        >>> evaluate_condition("items", {"items": ["a", "b"]})
        True
        >>> evaluate_condition("missing_slot", {})
        False
    """
    condition = condition.strip()

    # Handle AND/OR (case insensitive)
    and_match = re.search(r"\s+AND\s+", condition, re.IGNORECASE)
    if and_match:
        left = condition[: and_match.start()]
        right = condition[and_match.end() :]
        return evaluate_condition(left, slots) and evaluate_condition(right, slots)

    or_match = re.search(r"\s+OR\s+", condition, re.IGNORECASE)
    if or_match:
        left = condition[: or_match.start()]
        right = condition[or_match.end() :]
        return evaluate_condition(left, slots) or evaluate_condition(right, slots)

    # Handle parentheses (strip outer parens and recurse)
    if condition.startswith("(") and condition.endswith(")"):
        return evaluate_condition(condition[1:-1], slots)

    # Handle comparison operators
    for op_str, op_func in OPERATORS.items():
        if op_str in condition:
            return _evaluate_comparison(condition, op_str, op_func, slots)

    # Simple existence/truthiness check
    slot_name = condition.strip()
    value = slots.get(slot_name)
    return bool(value)


def _evaluate_comparison(
    condition: str,
    op_str: str,
    op_func: Any,
    slots: dict[str, Any],
) -> bool:
    """Evaluate a single comparison expression."""
    parts = condition.split(op_str, 1)
    if len(parts) != 2:
        logger.warning(f"Invalid comparison: {condition}")
        return False

    left_expr = parts[0].strip()
    right_expr = parts[1].strip()

    # Get left value (slot reference)
    left_val = slots.get(left_expr)

    # Parse right value (literal or slot reference)
    right_val = _parse_value(right_expr, slots)

    # 1. Handle Equality (None-safe)
    if op_str in ("==", "!="):
        # Allow None comparison and mixed types
        return bool(op_func(left_val, right_val))

    # 2. For ordering operators (<, >, <=, >=), missing slot means False
    if left_val is None:
        return False

    # 3. Try numeric comparison
    is_left_num, left_num = _to_number(left_val)
    is_right_num, right_num = _to_number(right_val)

    if is_left_num and is_right_num:
        return bool(op_func(left_num, right_num))

    # 4. Fallback: String comparison ONLY if both are strings
    if isinstance(left_val, str) and isinstance(right_val, str):
        return bool(op_func(left_val, right_val))

    # 5. Mismatched types for ordering -> False (e.g. "abc" > 10)
    return False


def _to_number(val: Any) -> tuple[bool, float | int | None]:
    """Try to convert value to number. Returns (success, value)."""
    if isinstance(val, (int, float)):
        return True, val
    if isinstance(val, str) and val.replace(".", "").replace("-", "").isdigit():
        try:
            return True, float(val) if "." in val else int(val)
        except ValueError:
            return False, None
    return False, None


def _parse_value(expr: str, slots: dict[str, Any]) -> Any:
    """Parse a value expression (literal or slot reference)."""
    expr = expr.strip()

    # String literal (quoted)
    if (expr.startswith("'") and expr.endswith("'")) or (
        expr.startswith('"') and expr.endswith('"')
    ):
        return expr[1:-1]

    # Numeric literal
    if expr.replace(".", "").replace("-", "").isdigit():
        return float(expr) if "." in expr else int(expr)

    # Boolean literals
    if expr.lower() == "true":
        return True
    if expr.lower() == "false":
        return False

    # None literal
    if expr.lower() == "none" or expr.lower() == "null":
        return None

    # Slot reference
    return slots.get(expr)
