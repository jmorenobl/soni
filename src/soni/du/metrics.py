"""Metrics for evaluating DSPy NLU modules."""

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
    """Calculate accuracy metric with textual feedback for GEPA optimization.

    GEPA benefits from textual feedback explaining what went wrong,
    in addition to the numeric score. This helps the reflection LM
    generate better instruction proposals.

    Args:
        gold: Ground truth example
        pred: Model prediction
        trace: Optional trace information
        pred_name: Optional predictor name (used by GEPA)
        pred_trace: Optional predictor trace (used by GEPA)

    Returns:
        dspy.Prediction with 'score' (float) and 'feedback' (str) attributes
    """
    score = intent_accuracy_metric(gold, pred)
    feedback = _generate_feedback(gold, pred, score)
    # GEPA expects a Prediction object with score and feedback attributes
    return dspy.Prediction(score=score, feedback=feedback)


def _generate_feedback(
    gold: dspy.Example,
    pred: dspy.Prediction,
    score: float,
) -> str:
    """Generate textual feedback explaining what went wrong.

    This feedback helps GEPA's reflection LM understand the errors
    and propose better instructions.

    Args:
        gold: Ground truth example
        pred: Model prediction
        score: Numeric score from intent_accuracy_metric

    Returns:
        Human-readable feedback string
    """
    if score >= 1.0:
        return "Perfect! All components matched correctly."

    expected = _extract_nlu_output(gold.result if hasattr(gold, "result") else None)
    predicted = _extract_nlu_output(pred.result if hasattr(pred, "result") else None)

    if expected is None or predicted is None:
        return "Missing result in example or prediction."

    issues = []

    # Check message_type mismatch
    expected_mt = _normalize_message_type(expected.message_type)
    predicted_mt = _normalize_message_type(predicted.message_type)
    if expected_mt != predicted_mt:
        issues.append(f"Wrong message_type: predicted '{predicted_mt}', expected '{expected_mt}'")

    # Check confirmation_value mismatch (critical for confirmation flow)
    if hasattr(expected, "confirmation_value") and hasattr(predicted, "confirmation_value"):
        if expected.confirmation_value != predicted.confirmation_value:
            issues.append(
                f"Wrong confirmation_value: predicted {predicted.confirmation_value}, "
                f"expected {expected.confirmation_value}"
            )

    # Check command mismatch
    expected_cmd = (expected.command or "").lower()
    predicted_cmd = (predicted.command or "").lower()
    if expected_cmd != predicted_cmd:
        issues.append(f"Wrong command: predicted '{predicted_cmd}', expected '{expected_cmd}'")

    # Check slots mismatch
    if not _compare_slots(expected.slots, predicted.slots):
        expected_slot_names = [
            s.get("name") if isinstance(s, dict) else getattr(s, "name", "?")
            for s in expected.slots
        ]
        predicted_slot_names = [
            s.get("name") if isinstance(s, dict) else getattr(s, "name", "?")
            for s in predicted.slots
        ]
        issues.append(
            f"Slot mismatch: predicted {predicted_slot_names}, expected {expected_slot_names}"
        )

    return ". ".join(issues) if issues else f"Partial match with score {score:.2f}"


def intent_accuracy_metric(
    example: dspy.Example,
    prediction: dspy.Prediction,
    trace: Any = None,  # noqa: ARG001
) -> float:
    """Calculate accuracy metric for NLU prediction.

    This metric evaluates the NLUOutput structure returned by the DialogueUnderstanding signature.
    It combines:
    - Message type accuracy (40% weight): Exact match of message_type (critical for routing)
    - Command accuracy (30% weight): Exact match of command (intent/flow name)
    - Slot accuracy (30% weight): Matching of extracted slots (name, value, action)

    Args:
        example: Ground truth example with expected NLUOutput in result field
        prediction: Model prediction with NLUOutput in result field
        trace: Optional trace information (unused for now)

    Returns:
        Score between 0.0 and 1.0, where 1.0 is perfect match
    """
    try:
        # Extract NLUOutput from example and prediction
        # Handle both NLUOutput objects and dicts (DSPy may return dicts)
        expected_result = _extract_nlu_output(
            example.result if hasattr(example, "result") else None
        )
        predicted_result = _extract_nlu_output(
            prediction.result if hasattr(prediction, "result") else None
        )

        if expected_result is None or predicted_result is None:
            logger.warning(
                "Missing result field in example or prediction",
                extra={
                    "has_example_result": expected_result is not None,
                    "has_prediction_result": predicted_result is not None,
                },
            )
            return 0.0

        # 1. Compare message_type (40% weight) - CRITICAL for routing
        # Handle both enum and string comparisons
        expected_mt = _normalize_message_type(expected_result.message_type)
        predicted_mt = _normalize_message_type(predicted_result.message_type)
        message_type_match = expected_mt == predicted_mt

        # 2. Compare command (30% weight) - Intent/flow name
        # Both None is a match, both same string is a match
        expected_command = expected_result.command or ""
        predicted_command = predicted_result.command or ""
        command_match = expected_command.lower() == predicted_command.lower()

        # 3. Compare slots (30% weight) - Extracted slot values
        slot_match = _compare_slots(expected_result.slots, predicted_result.slots)

        # Weighted score: 40% message_type, 30% command, 30% slots
        score = (
            0.4 * (1.0 if message_type_match else 0.0)
            + 0.3 * (1.0 if command_match else 0.0)
            + 0.3 * (1.0 if slot_match else 0.0)
        )

        return score
    except (AttributeError, KeyError, TypeError, ValueError) as e:
        logger.warning(
            f"Error calculating metric: {e}",
            exc_info=True,
            extra={"error_type": type(e).__name__},
        )
        return 0.0


def _extract_nlu_output(result: Any) -> "NLUOutput | None":
    """Extract NLUOutput from result, handling both objects and dicts.

    Args:
        result: Can be NLUOutput, dict, or None

    Returns:
        NLUOutput object or None if extraction fails
    """
    from soni.du.models import NLUOutput

    if result is None:
        return None

    # Already an NLUOutput object
    if isinstance(result, NLUOutput):
        return result

    # Try to convert from dict
    if isinstance(result, dict):
        try:
            return cast("NLUOutput", NLUOutput.model_validate(result))
        except (ValueError, TypeError, AttributeError) as e:
            logger.warning(f"Failed to convert dict to NLUOutput: {e}")
            return None

    return None


def _normalize_message_type(message_type: Any) -> str:
    """Normalize message_type to string for comparison.

    Args:
        message_type: Can be MessageType enum, string, or other

    Returns:
        Normalized string value
    """
    from soni.du.models import MessageType

    if isinstance(message_type, MessageType):
        return message_type.value
    if isinstance(message_type, str):
        return message_type.lower()
    return str(message_type).lower()


def _compare_slots(expected_slots: list, predicted_slots: list) -> bool:
    """Compare two lists of SlotValue objects or dicts for matching.

    Args:
        expected_slots: Expected slot values (list of SlotValue or dict)
        predicted_slots: Predicted slot values (list of SlotValue or dict)

    Returns:
        True if slots match, False otherwise
    """
    try:
        # If both empty, it's a match
        if not expected_slots and not predicted_slots:
            return True

        # If one is empty and the other isn't, it's a mismatch
        if not expected_slots or not predicted_slots:
            return False

        # If different lengths, it's a mismatch
        if len(expected_slots) != len(predicted_slots):
            return False

        # Normalize slots to dicts for easier comparison
        # Handle both SlotValue objects and dicts
        expected_dict = {}
        for slot in expected_slots:
            if isinstance(slot, dict):
                name = slot.get("name", "")
                value = str(slot.get("value", "")).lower()
            else:
                name = getattr(slot, "name", "")
                value = str(getattr(slot, "value", "")).lower()
            if name:
                expected_dict[name] = value

        predicted_dict = {}
        for slot in predicted_slots:
            if isinstance(slot, dict):
                name = slot.get("name", "")
                value = str(slot.get("value", "")).lower()
            else:
                name = getattr(slot, "name", "")
                value = str(getattr(slot, "value", "")).lower()
            if name:
                predicted_dict[name] = value

        # Check all expected slots are present with matching values
        for name, expected_value in expected_dict.items():
            if name not in predicted_dict:
                return False
            predicted_value = predicted_dict[name]
            # Allow fuzzy matching (substring or exact match)
            if expected_value and predicted_value:
                if expected_value not in predicted_value and predicted_value not in expected_value:
                    return False
            elif expected_value != predicted_value:
                # Both empty strings should match
                return False

        return True
    except (AttributeError, KeyError, TypeError, ValueError):
        return False
