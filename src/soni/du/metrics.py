"""Metrics for evaluating DSPy NLU modules"""

import json
from typing import Any

import dspy


def intent_accuracy_metric(
    example: dspy.Example,
    prediction: dspy.Prediction,
    trace: Any = None,  # noqa: ARG001
) -> float:
    """
    Calculate accuracy metric for intent extraction and slot filling.

    This metric combines:
    - Intent accuracy (70% weight): Exact match of structured_command
    - Slot accuracy (30% weight): Key-value matching of extracted slots

    Args:
        example: Ground truth example with expected outputs
        prediction: Model prediction to evaluate
        trace: Optional trace information (unused for now)

    Returns:
        Score between 0.0 and 1.0, where 1.0 is perfect match
    """
    try:
        # Compare structured_command (intent)
        expected_intent = (
            example.structured_command.lower()
            if hasattr(example, "structured_command") and example.structured_command
            else ""
        )
        predicted_intent = (
            prediction.structured_command.lower()
            if hasattr(prediction, "structured_command") and prediction.structured_command
            else ""
        )

        intent_match = expected_intent == predicted_intent

        # Compare extracted slots (basic JSON comparison)
        try:
            example_slots = (
                json.loads(example.extracted_slots)
                if hasattr(example, "extracted_slots") and example.extracted_slots
                else {}
            )
            pred_slots = (
                json.loads(prediction.extracted_slots)
                if hasattr(prediction, "extracted_slots") and prediction.extracted_slots
                else {}
            )

            # Check if key entities match (simplified)
            slot_match = True
            if example_slots:
                for key in example_slots:
                    if key not in pred_slots:
                        slot_match = False
                        break
                    # Allow fuzzy matching for values (case-insensitive substring)
                    expected_value = str(example_slots[key]).lower()
                    predicted_value = str(pred_slots[key]).lower()
                    if expected_value not in predicted_value:
                        slot_match = False
                        break
            elif pred_slots:
                # If example has no slots but prediction does, it's a mismatch
                slot_match = False
        except (json.JSONDecodeError, AttributeError, TypeError, KeyError):
            slot_match = False

        # Weighted score: 70% intent, 30% slots
        score = 0.7 * (1.0 if intent_match else 0.0) + 0.3 * (1.0 if slot_match else 0.0)
        return score
    except Exception:
        # Return 0.0 for any error in metric calculation
        return 0.0
