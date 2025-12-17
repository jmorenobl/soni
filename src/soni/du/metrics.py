"""NLU evaluation metrics for DSPy optimization.

Provides granular metrics that measure command correctness with partial scoring,
rather than all-or-nothing evaluation.
"""

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from soni.core.commands import Command
from soni.du.models import NLUOutput


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


# Fields that are "key" vs "auxiliary" per command type
KEY_FIELDS = {
    "start_flow": ["flow_name"],
    "set_slot": ["slot"],
    "correct_slot": ["slot"],
    "cancel_flow": [],
    "affirm": [],
    "deny": ["slot_to_change"],
    "clarify": [],
    "chitchat": [],
}

VALUE_FIELDS = {
    "start_flow": ["slots"],
    "set_slot": ["value"],
    "correct_slot": ["new_value"],
    "cancel_flow": ["reason"],
    "affirm": [],
    "deny": [],
    "clarify": ["topic"],
    "chitchat": ["message"],
}


def score_command_pair(expected: Command, actual: Command) -> MetricScore:
    """Score how well actual command matches expected.

    Breakdown:
    - type_score: 1.0 if same type, 0.0 otherwise
    - field_score: Proportion of key fields that match
    - value_score: Proportion of value fields that match (fuzzy)

    Weights: type=50%, field=30%, value=20%
    """
    exp_data = expected.model_dump()
    act_data = actual.model_dump()

    cmd_type = exp_data.get("type", "")

    # Type score
    if type(expected) is type(actual):
        type_score = 1.0
    else:
        # Wrong type = everything is wrong
        return MetricScore(type_score=0.0, field_score=0.0, value_score=0.0, total=0.0)

    # Field score (key fields like slot_name, flow_name)
    key_fields = KEY_FIELDS.get(cmd_type, [])
    if key_fields:
        field_matches = sum(
            1.0 if normalize_value(exp_data.get(f)) == normalize_value(act_data.get(f)) else 0.0
            for f in key_fields
        )
        field_score = field_matches / len(key_fields)
    else:
        field_score = 1.0  # No key fields = automatic pass

    # Value score (values with fuzzy matching)
    value_fields = VALUE_FIELDS.get(cmd_type, [])
    if value_fields:
        value_matches = sum(compare_values(exp_data.get(f), act_data.get(f)) for f in value_fields)
        value_score = value_matches / len(value_fields)
    else:
        value_score = 1.0  # No value fields = automatic pass

    # Weighted total: type matters most, then key fields, then values
    total = (type_score * 0.5) + (field_score * 0.3) + (value_score * 0.2)

    return MetricScore(
        type_score=type_score,
        field_score=field_score,
        value_score=value_score,
        total=total,
    )


def score_command_lists(
    expected: list[Command],
    actual: list[Command],
) -> float:
    """Score two command lists using best-match pairing.

    Strategy:
    1. For each expected command, find the best matching actual command
    2. Average the best match scores
    3. Apply penalty for extra/missing commands

    Returns:
        float: 0.0 to 1.0 score
    """
    if not expected and not actual:
        return 1.0  # Both empty = perfect match

    if not expected:
        return 0.0  # No expected but got commands = wrong

    if not actual:
        return 0.0  # Expected commands but got none = wrong

    # Score each expected command against best actual match
    matched_indices: set[int] = set()
    total_score = 0.0

    for exp_cmd in expected:
        best_score = 0.0
        best_idx = -1

        for idx, act_cmd in enumerate(actual):
            if idx in matched_indices:
                continue  # Already used

            score = score_command_pair(exp_cmd, act_cmd)
            if score.total > best_score:
                best_score = score.total
                best_idx = idx

        if best_idx >= 0:
            matched_indices.add(best_idx)

        total_score += best_score

    # Base score: average of best matches
    base_score = total_score / len(expected)

    # Penalty for extra commands (mild)
    extra_commands = len(actual) - len(expected)
    if extra_commands > 0:
        penalty = 0.1 * extra_commands  # 10% penalty per extra command
        base_score = max(0.0, base_score - penalty)

    return base_score


def create_granular_metric() -> Callable[[Any, Any, Any], float]:
    """Create a granular metric function for DSPy optimization.

    Returns a metric that scores predictions on a 0-1 scale with
    partial credit for partially correct outputs.
    """

    def metric(example: Any, prediction: Any, trace: Any = None) -> float:
        """Evaluate prediction with granular scoring.

        Returns:
            float: 0.0 to 1.0 score
        """
        try:
            # Get expected commands from example
            if not hasattr(example, "result") or example.result is None:
                return 0.0
            expected_commands: list[Command] = example.result.commands

            # Handle prediction - could be NLUOutput or Prediction wrapper
            if isinstance(prediction, NLUOutput):
                actual_commands = prediction.commands
            elif hasattr(prediction, "result") and isinstance(prediction.result, NLUOutput):
                actual_commands = prediction.result.commands
            elif hasattr(prediction, "commands"):
                actual_commands = prediction.commands
            else:
                return 0.0

            return score_command_lists(expected_commands, list(actual_commands))

        except (AttributeError, TypeError):
            return 0.0

    return metric


def create_strict_metric() -> Callable[[Any, Any, Any], bool]:
    """Create a strict binary metric (original behavior).

    Returns True only if all commands match exactly.
    """

    def metric(example: Any, prediction: Any, trace: Any = None) -> bool:
        """Strict all-or-nothing evaluation."""
        score = create_granular_metric()(example, prediction, trace)
        return score >= 0.99  # Essentially perfect match

    return metric


# Default metric for optimization
default_metric = create_granular_metric()


def adapt_metric_for_gepa(metric_fn: Callable) -> Callable:
    """Adapt a standard (example, pred, trace) metric for GEPA.

    GEPA requires a metric with the signature:
    (gold, pred, trace, pred_name, pred_trace)

    Args:
        metric_fn: Standard metric function returning a float

    Returns:
        Wrapped metric function compatible with GEPA
    """

    def gepa_wrapper(
        gold: Any,
        pred: Any,
        trace: Any = None,
        pred_name: str | None = None,
        pred_trace: Any | None = None,
    ) -> float:
        return float(metric_fn(gold, pred, trace))

    return gepa_wrapper
