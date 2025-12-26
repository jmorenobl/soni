"""MIPROv2 optimizer for SoniDU.

Uses DSPy's latest MIPROv2 for prompt optimization.
"""

from collections.abc import Callable
from typing import Any, cast

import dspy
from dspy import Example
from dspy.teleprompt import MIPROv2

from soni.core.commands import Command
from soni.du.metrics.adapters import adapt_metric_for_gepa
from soni.du.models import NLUOutput
from soni.du.modules import SoniDU
from soni.du.slot_extractor import SlotExtractor


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


def _create_gepa_optimizer(
    metric: Callable,
    auto: str,
    reflection_lm: Any,
    seed: int = 42,
    verbose: bool = True,  # Consumed here, not passed to GEPA
    reflection_minibatch_size: int = 5,  # Better context for NLU errors
    **kwargs: Any,
) -> dspy.GEPA:
    """Create GEPA optimizer instance."""
    # GEPA requires specific metric signature
    gepa_metric = adapt_metric_for_gepa(metric)

    return dspy.GEPA(
        metric=gepa_metric,
        auto=auto,
        reflection_lm=reflection_lm,
        track_stats=True,
        seed=seed,
        reflection_minibatch_size=reflection_minibatch_size,
        **kwargs,
    )


def _create_miprov2_optimizer(
    metric: Callable,
    auto: str,
    prompt_model: Any,
    teacher_model: Any,
    seed: int = 42,
    verbose: bool = True,
    **kwargs: Any,
) -> MIPROv2:
    """Create MIPROv2 optimizer instance."""
    return MIPROv2(
        metric=metric,
        auto=auto,
        prompt_model=prompt_model,
        teacher_settings={"lm": teacher_model} if teacher_model else {},
        verbose=verbose,
        track_stats=True,
        **kwargs,
    )


def optimize_du(
    trainset: list[Example],
    metric: Callable,
    valset: list[Example] | None = None,
    auto: str = "medium",  # "light", "medium", "heavy"
    prompt_model=None,
    teacher_model=None,
    max_bootstrapped_demos: int = 6,
    max_labeled_demos: int = 4,
    num_threads: int = 6,
    init_temperature: float = 0.8,
    verbose: bool = True,
    optimizer_type: str = "miprov2",  # "miprov2" or "gepa"
) -> SoniDU:
    """Optimize SoniDU with chosen optimizer strategy.

    Args:
        trainset: Training examples
        metric: Evaluation metric function
        valset: Validation examples (optional, recommended for GEPA)
        auto: Optimization intensity ("light", "medium", "heavy")
        prompt_model: LLM for prompts (MIPROv2)
        teacher_model: LLM for teacher (MIPROv2) or reflection (GEPA)
        max_bootstrapped_demos: Max demos to bootstrap
        max_labeled_demos: Max demos from training set
        num_threads: Parallel threads
        init_temperature: Bootstrapping temp
        verbose: Show progress
        optimizer_type: "miprov2" or "gepa"

    Returns:
        Optimized SoniDU module
    """
    if optimizer_type.lower() == "gepa":
        teleprompter = _create_gepa_optimizer(
            metric=metric,
            auto=auto,
            reflection_lm=teacher_model,
            num_threads=num_threads,
            verbose=verbose,  # Passed to GEPA via kwargs if supported in future, or ignored if fixed
            # Note: verbose removed for now as it causes error in current version
        )
    else:
        teleprompter = _create_miprov2_optimizer(
            metric=metric,
            auto=auto,
            prompt_model=prompt_model,
            teacher_model=teacher_model,
            max_bootstrapped_demos=max_bootstrapped_demos,
            max_labeled_demos=max_labeled_demos,
            num_threads=num_threads,
            init_temperature=init_temperature,
            verbose=verbose,
        )

    program = SoniDU()

    # Compile optimizations
    compile_kwargs = {
        "student": program.deepcopy(),
        "trainset": trainset,
    }

    if valset:
        compile_kwargs["valset"] = valset

    if optimizer_type.lower() != "gepa":
        # MIPROv2 specific arg
        compile_kwargs["requires_permission_to_run"] = False

    optimized = teleprompter.compile(**compile_kwargs)

    return cast(SoniDU, optimized)


def optimize_slot_extractor(
    trainset: list[Example],
    metric: Callable,
    valset: list[Example] | None = None,
    auto: str = "light",  # Extraction is simpler, light usually sufficient
    prompt_model=None,
    teacher_model=None,
    max_bootstrapped_demos: int = 4,
    max_labeled_demos: int = 4,
    num_threads: int = 6,
    init_temperature: float = 0.8,
    verbose: bool = True,
    optimizer_type: str = "miprov2",
) -> SlotExtractor:
    """Optimize SlotExtractor with chosen optimizer strategy.

    Args:
        trainset: Training examples
        metric: Evaluation metric function
        valset: Validation examples
        auto: Optimization intensity
        prompt_model: LLM for prompts
        teacher_model: LLM for teacher
        optimizer_type: "miprov2" or "gepa"

    Returns:
        Optimized SlotExtractor module
    """
    from soni.du.slot_extractor import SlotExtractor

    if optimizer_type.lower() == "gepa":
        teleprompter = _create_gepa_optimizer(
            metric=metric,
            auto=auto,
            reflection_lm=teacher_model,
            num_threads=num_threads,
            verbose=verbose,
        )
    else:
        teleprompter = _create_miprov2_optimizer(
            metric=metric,
            auto=auto,
            prompt_model=prompt_model,
            teacher_model=teacher_model,
            max_bootstrapped_demos=max_bootstrapped_demos,
            max_labeled_demos=max_labeled_demos,
            num_threads=num_threads,
            init_temperature=init_temperature,
            verbose=verbose,
        )

    # SlotExtractor usually works well without COT for simpler flows,
    # but optimizer can tune COT if useful.
    # We initialize student without COT to start simple.
    program = SlotExtractor(use_cot=False)

    # Compile optimizations
    compile_kwargs = {
        "student": program.deepcopy(),  # Start fresh
        "trainset": trainset,
    }

    if valset:
        compile_kwargs["valset"] = valset

    if optimizer_type.lower() != "gepa":
        compile_kwargs["requires_permission_to_run"] = False

    optimized = teleprompter.compile(**compile_kwargs)

    return cast(SlotExtractor, optimized)
