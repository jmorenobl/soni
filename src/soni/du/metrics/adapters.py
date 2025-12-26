"""Metric adapters for GEPA and SlotExtractor."""

from collections.abc import Callable
from typing import Any

from soni.du.metrics.core import normalize_value


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


def create_slot_extraction_metric() -> Callable[[Any, Any, Any], float]:
    """Create a metric for SlotExtractor optimization.

    Scores extracted slots based on set overlap (exact match of slot+value).

    Returns:
        float: 0.0 to 1.0 score (Intersection over Union-like)
    """

    def metric(example: Any, prediction: Any, trace: Any = None) -> float:
        """Evaluate slot extraction."""
        try:
            # Expected
            if not hasattr(example, "result") or example.result is None:
                return 0.0
            expected_slots = example.result.extracted_slots

            # Predicted
            extracted_slots = []
            if hasattr(prediction, "extracted_slots"):
                # Direct object
                extracted_slots = prediction.extracted_slots
            elif hasattr(prediction, "result") and hasattr(prediction.result, "extracted_slots"):
                # Wrapped in Prediction
                extracted_slots = prediction.result.extracted_slots

            # Normalize and create sets for comparison
            # set of (slot, value) tuples
            exp_set = {
                (normalize_value(s.get("slot")), normalize_value(s.get("value")))
                for s in expected_slots
            }
            act_set = {
                (normalize_value(s.get("slot")), normalize_value(s.get("value")))
                for s in extracted_slots
            }

            if not exp_set and not act_set:
                return 1.0

            # Score = Correct / Max(Expected, Actual)
            # This penalizes both missing slots and extra hallucinations
            correct = len(exp_set & act_set)
            denominator = max(len(exp_set), len(act_set))

            if denominator == 0:
                return 0.0

            return float(correct) / denominator

        except (AttributeError, TypeError):
            return 0.0

    return metric
