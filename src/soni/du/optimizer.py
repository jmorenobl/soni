"""MIPROv2 optimizer for SoniDU.

Uses DSPy's latest MIPROv2 for prompt optimization.
"""

from collections.abc import Callable
from typing import cast

from dspy import Example
from dspy.teleprompt import MIPROv2

from soni.du.models import Command, NLUOutput
from soni.du.modules import SoniDU


def create_metric(validate_command_fn: Callable[[Command, Command], bool]) -> Callable:
    """Create a metric function for optimization.

    Args:
        validate_command_fn: Function to validate if command matches expected
                             (expected_cmd, actual_cmd) -> bool
    """

    def metric(example: Example, prediction: NLUOutput, trace=None) -> bool:
        # prediction is the return value of forward(), which is NLUOutput
        # But DSPy optimizer sometimes unwraps it or passes Prediction object?
        # In our SoniDU.forward, we return NLUOutput directly.

        # example.expected_commands should be list[Command]
        expected = example.expected_commands
        actual = prediction.commands

        if len(expected) != len(actual):
            return False

        for exp, act in zip(expected, actual, strict=True):
            if not validate_command_fn(exp, act):
                return False

        return True

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
