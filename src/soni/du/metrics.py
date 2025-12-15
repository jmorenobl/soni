"""Metrics for evaluating DSPy NLU modules (v2.0 Command-Based)."""

import logging
from typing import TYPE_CHECKING, Any, cast

import dspy

if TYPE_CHECKING:
    from soni.du.models import NLUOutput

logger = logging.getLogger(__name__)


def gepa_feedback_metric(
    gold: dspy.Example,
    pred: dspy.Prediction,
    trace: Any = None,
    pred_name: str | None = None,
    pred_trace: Any = None,
) -> dspy.Prediction:
    """Calculate accuracy metric with textual feedback for GEPA optimization."""
    score = intent_accuracy_metric(gold, pred)
    feedback = _generate_feedback(gold, pred, score)
    return dspy.Prediction(score=score, feedback=feedback)


def _generate_feedback(
    gold: dspy.Example,
    pred: dspy.Prediction,
    score: float,
) -> str:
    """Generate textual feedback on command mismatches."""
    if score >= 1.0:
        return "Perfect! Commands matched."

    expected = _extract_nlu_output(gold.result if hasattr(gold, "result") else None)
    predicted = _extract_nlu_output(pred.result if hasattr(pred, "result") else None)

    if expected is None or predicted is None:
        return "Missing result in example or prediction."

    issues = []

    # Compare commands lists
    exp_cmds = [c.type for c in expected.commands]
    pred_cmds = [c.type for c in predicted.commands]

    if exp_cmds != pred_cmds:
        issues.append(f"Command type mismatch: expected {exp_cmds}, got {pred_cmds}")
    else:
        # If types match, check content
        # Simple string comparison of commands for now
        exp_strs = [str(c) for c in expected.commands]
        pred_strs = [str(c) for c in predicted.commands]
        if exp_strs != pred_strs:
            issues.append(f"Command content mismatch: {pred_strs} vs {exp_strs}")

    return ". ".join(issues) if issues else f"Partial match score {score:.2f}"


def intent_accuracy_metric(
    example: dspy.Example,
    prediction: dspy.Prediction,
    trace: Any = None,
) -> float:
    """Calculate accuracy metric for Command generation.

    Score 1.0 if the sequence of commands matches exactly.
    """
    try:
        expected_result = _extract_nlu_output(
            example.result if hasattr(example, "result") else None
        )
        predicted_result = _extract_nlu_output(
            prediction.result if hasattr(prediction, "result") else None
        )

        if expected_result is None or predicted_result is None:
            return 0.0

        # Exact list match
        # Rely on Pydantic equality for commands
        if expected_result.commands == predicted_result.commands:
            return 1.0

        return 0.0

    except Exception as e:
        logger.warning(f"Error calculating metric: {e}")
        return 0.0


def _extract_nlu_output(result: Any) -> "NLUOutput | None":
    """Extract NLUOutput from result."""
    from soni.du.models import NLUOutput

    if result is None:
        return None

    if isinstance(result, NLUOutput):
        return result

    if isinstance(result, dict):
        try:
            return cast("NLUOutput", NLUOutput.model_validate(result))
        except Exception:
            return None

    return None
