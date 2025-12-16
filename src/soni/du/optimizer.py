"""MIPROv2 optimizer for SoniDU.

Uses DSPy's latest MIPROv2 for prompt optimization.
"""

from collections.abc import Callable
from typing import Any, cast

from dspy import Example
from dspy.teleprompt import MIPROv2

from soni.core.commands import Command
from soni.du.models import NLUOutput
from soni.du.modules import SoniDU


def default_command_validator(expected: Command, actual: Command) -> bool:
    """Validate that two commands match by type and key fields.

    Compares command type and important fields (slot names, flow names, etc.)
    but ignores auxiliary fields like confidence scores.
    """
    if type(expected) is not type(actual):
        return False

    # Compare relevant fields based on command type
    # Using model_dump() to get dict representation
    expected_data = expected.model_dump(exclude={"confidence"})
    actual_data = actual.model_dump(exclude={"confidence"})

    return expected_data == actual_data


def create_metric(
    validate_command_fn: Callable[[Command, Command], bool] | None = None,
) -> Callable[[Example, Any, Any], bool]:
    """Create a metric function for optimization.

    Args:
        validate_command_fn: Function to validate if command matches expected.
                             Defaults to default_command_validator.
    """
    validator = validate_command_fn or default_command_validator

    def metric(example: Example, prediction: Any, trace: Any = None) -> bool:
        """Evaluate if prediction matches expected output."""
        try:
            # Get expected commands from example
            if not hasattr(example, "result") or example.result is None:
                return False
            expected_commands: list[Command] = example.result.commands

            # Handle prediction - could be NLUOutput or Prediction wrapper
            if isinstance(prediction, NLUOutput):
                actual_commands = prediction.commands
            elif hasattr(prediction, "result") and isinstance(prediction.result, NLUOutput):
                actual_commands = prediction.result.commands
            elif hasattr(prediction, "commands"):
                actual_commands = prediction.commands
            else:
                return False

            # Compare command lists
            if len(expected_commands) != len(actual_commands):
                return False

            return all(
                validator(exp, act)
                for exp, act in zip(expected_commands, actual_commands, strict=True)
            )

        except (AttributeError, TypeError):
            return False

    return metric


def optimize_du(
    trainset: list[Example],
    metric: Callable,
    auto: str = "light",  # "light", "medium", "heavy"
    prompt_model=None,
    teacher_model=None,
) -> SoniDU:
    """Optimize SoniDU with MIPROv2.

    Args:
        trainset: Training examples (dspy.Example objects)
        metric: Evaluation metric function
        auto: Optimization intensity
        prompt_model: LLM to use for prompt generation
        teacher_model: LLM to use for teacher

    Returns:
        Optimized SoniDU module
    """
    # Note: MIPROv2 requires prompt_model and teacher settings if not default
    teleprompter = MIPROv2(
        metric=metric,
        auto=auto,
        prompt_model=prompt_model,
        teacher_settings={"lm": teacher_model} if teacher_model else {},
    )

    program = SoniDU()

    # Compile optimizations
    # Note: max_bootstrapped_demos etc. are controlled by 'auto' setting or kwargs
    optimized = teleprompter.compile(
        program.deepcopy(),
        trainset=trainset,
        requires_permission_to_run=False,
    )

    return cast(SoniDU, optimized)
