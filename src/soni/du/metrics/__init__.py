"""Metrics module for NLU evaluation.

This module provides tools for computing metrics on NLU outputs,
particularly for DSPy optimization.
"""

from soni.du.metrics.adapters import (
    adapt_metric_for_gepa,
    create_slot_extraction_metric,
)
from soni.du.metrics.core import (
    MetricScore,
    compare_values,
    normalize_value,
)
from soni.du.metrics.factory import (
    create_granular_metric,
    create_strict_metric,
    default_metric,
)
from soni.du.metrics.registry import (
    KEY_FIELDS,
    VALUE_FIELDS,
    FieldRegistry,
)
from soni.du.metrics.scoring import (
    score_command_lists,
    score_command_pair,
)

__all__ = [
    # Core
    "MetricScore",
    "normalize_value",
    "compare_values",
    # Registry
    "FieldRegistry",
    "KEY_FIELDS",
    "VALUE_FIELDS",
    # Scoring
    "score_command_pair",
    "score_command_lists",
    # Factory
    "create_granular_metric",
    "create_strict_metric",
    "default_metric",
    # Adapters
    "adapt_metric_for_gepa",
    "create_slot_extraction_metric",
]
