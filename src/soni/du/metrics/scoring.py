"""Scoring functions for command comparison."""

from soni.core.commands import Command
from soni.du.metrics.core import MetricScore, compare_values, normalize_value
from soni.du.metrics.registry import KEY_FIELDS, VALUE_FIELDS


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
