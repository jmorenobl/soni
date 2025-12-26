"""Metric functions for DSPy optimization."""

from collections.abc import Callable
from typing import Any

from soni.core.commands import Command
from soni.du.metrics.scoring import score_command_lists
from soni.du.models import NLUOutput


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
