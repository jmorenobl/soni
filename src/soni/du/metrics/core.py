"""Core metric types and utilities."""

from dataclasses import dataclass
from typing import Any


@dataclass
class MetricScore:
    """Detailed breakdown of metric scoring."""

    type_score: float  # Did we get the right command type?
    field_score: float  # Did we get the right key fields (slot_name, flow_name)?
    value_score: float  # Did we get the right values?
    total: float  # Weighted combination

    def __repr__(self) -> str:
        return f"Score(type={self.type_score:.2f}, field={self.field_score:.2f}, value={self.value_score:.2f}, total={self.total:.2f})"


def normalize_value(value: Any) -> str:
    """Normalize a value for comparison.

    - Lowercase
    - Strip whitespace
    - Convert None to empty string
    """
    if value is None:
        return ""
    return str(value).lower().strip()


def compare_values(expected: Any, actual: Any) -> float:
    """Compare two values with fuzzy matching.

    Returns:
        1.0: Exact match (after normalization)
        0.5: Partial match (one contains the other)
        0.0: No match
    """
    exp_norm = normalize_value(expected)
    act_norm = normalize_value(actual)

    if exp_norm == act_norm:
        return 1.0

    # Partial match: one contains the other
    if exp_norm in act_norm or act_norm in exp_norm:
        return 0.5

    return 0.0
