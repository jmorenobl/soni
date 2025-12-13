"""DSPy optimization pipeline for SoniDU modules."""

import logging
import time
from pathlib import Path
from typing import Any

import dspy
from dspy.teleprompt import GEPA, MIPROv2

from soni.du.metrics import gepa_feedback_metric, intent_accuracy_metric
from soni.du.modules import SoniDU

logger = logging.getLogger(__name__)


def optimize_soni_du(
    trainset: list[dspy.Example],
    optimizer_type: str = "MIPROv2",
    num_trials: int = 10,
    timeout_seconds: int = 600,
    output_dir: Path | str | None = None,
    minibatch_size: int | None = None,
    num_candidates: int | None = None,
    max_bootstrapped_demos: int = 6,
    max_labeled_demos: int = 8,
    init_temperature: float = 1.0,
) -> tuple[SoniDU, dict[str, Any]]:
    """Optimize a SoniDU module using DSPy optimizers.

    Args:
        trainset: List of dspy.Example instances for training
        optimizer_type: Type of optimizer to use (\"MIPROv2\" or \"GEPA\")
        num_trials: Number of optimization trials
        timeout_seconds: Maximum time for optimization in seconds
        output_dir: Optional directory to save optimized module
        minibatch_size: Optional minibatch size for MIPROv2. Auto-calculated if None.
        num_candidates: Number of candidate prompts to evaluate. Defaults to 1.5x num_trials.
        max_bootstrapped_demos: Maximum bootstrapped demonstrations. Default: 6.
        max_labeled_demos: Maximum labeled demonstrations. Default: 8.
        init_temperature: Initial temperature for Bayesian optimization. Default: 1.0.

    Returns:
        Tuple of (optimized SoniDU module, metrics dictionary)

    Raises:
        ValueError: If optimizer_type is not supported
        RuntimeError: If optimization fails
    """
    if optimizer_type not in ("MIPROv2", "GEPA"):
        raise ValueError(f"Unsupported optimizer type: {optimizer_type}. Supported: MIPROv2, GEPA")

    # Create baseline module
    baseline_nlu = SoniDU()

    # Evaluate baseline
    print("Evaluating baseline...")
    baseline_start = time.time()
    baseline_score = _evaluate_module(baseline_nlu, trainset)
    baseline_time = time.time() - baseline_start

    print(f"Baseline accuracy: {baseline_score:.2%} (time: {baseline_time:.2f}s)")

    # Configure and run optimizer based on type
    print(f"Optimizing with {optimizer_type} ({num_trials} trials)...")
    optimization_start = time.time()

    try:
        if optimizer_type == "GEPA":
            optimized_nlu = _optimize_with_gepa(baseline_nlu, trainset, num_trials, timeout_seconds)
        else:  # MIPROv2
            optimized_nlu = _optimize_with_miprov2(
                baseline_nlu,
                trainset,
                num_trials,
                minibatch_size,
                num_candidates,
                max_bootstrapped_demos,
                max_labeled_demos,
                init_temperature,
            )
        optimization_time = time.time() - optimization_start
    except (ValueError, TypeError, AttributeError, RuntimeError) as e:
        # Errores esperados de optimización
        raise RuntimeError(f"Optimization failed: {e}") from e
    except Exception as e:
        # Errores inesperados
        logger.error(f"Unexpected optimization error: {e}", exc_info=True)
        raise RuntimeError(f"Optimization failed: {e}") from e

    if optimization_time > timeout_seconds:
        print(f"Warning: Optimization exceeded timeout ({timeout_seconds}s)")

    # Evaluate optimized module
    print("Evaluating optimized module...")
    optimized_start = time.time()
    optimized_score = _evaluate_module(optimized_nlu, trainset)
    optimized_time = time.time() - optimized_start

    print(f"Optimized accuracy: {optimized_score:.2%} (time: {optimized_time:.2f}s)")

    # Calculate improvement
    improvement = optimized_score - baseline_score
    improvement_pct = improvement * 100

    print(f"Improvement: {improvement_pct:+.1f}%")

    # Save optimized module if output_dir is provided
    if output_dir:
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        module_path = output_path / "optimized_nlu.json"
        optimized_nlu.save(str(module_path))
        print(f"Optimized module saved to: {module_path}")

    # Compile metrics
    metrics = {
        "baseline_accuracy": baseline_score,
        "optimized_accuracy": optimized_score,
        "improvement": improvement,
        "improvement_pct": improvement_pct,
        "baseline_time": baseline_time,
        "optimization_time": optimization_time,
        "optimized_eval_time": optimized_time,
        "total_time": time.time() - baseline_start,
        "num_trials": num_trials,
        "trainset_size": len(trainset),
    }

    return optimized_nlu, metrics


def _optimize_with_gepa(
    baseline_nlu: SoniDU,
    trainset: list[dspy.Example],
    num_trials: int,
    timeout_seconds: int,
) -> SoniDU:
    """Optimize using GEPA (Reflective Prompt Evolution).

    GEPA uses natural language feedback to evolve prompts through reflection,
    without relying on examples or demonstrations. It's more sample-efficient
    and can outperform MIPROv2 by >10% in some benchmarks.

    Args:
        baseline_nlu: Baseline SoniDU module
        trainset: Training examples for evaluation
        num_trials: Number of optimization trials
        timeout_seconds: Maximum optimization time

    Returns:
        Optimized SoniDU module
    """

    # Create a reflection LM for GEPA - this generates instruction proposals
    # Using GPT-4o with higher temperature for diverse proposals
    # DSPy best practice: strong reflection LM improves optimization quality
    reflection_lm = dspy.LM(
        model="openai/gpt-4o",
        temperature=1.0,
        max_tokens=8000,  # Increased for complex instructions
    )

    # Calculate appropriate minibatch size based on dataset
    # DSPy best practice: minibatch should be 3-5 for small datasets
    minibatch = min(5, max(3, len(trainset) // 10))

    optimizer = GEPA(
        metric=gepa_feedback_metric,  # Uses textual feedback for better reflection
        auto="medium",  # Balanced optimization budget
        reflection_lm=reflection_lm,
        reflection_minibatch_size=minibatch,
        track_stats=True,  # Track detailed optimization statistics
        skip_perfect_score=True,  # Skip examples with perfect score during reflection
        use_merge=True,  # Enable merge-based optimization
        seed=42,  # Reproducibility
    )

    result = optimizer.compile(
        student=baseline_nlu,
        trainset=trainset,
    )
    return result  # type: ignore[no-any-return]


def _optimize_with_miprov2(
    baseline_nlu: SoniDU,
    trainset: list[dspy.Example],
    num_trials: int,
    minibatch_size: int | None,
    num_candidates: int | None,
    max_bootstrapped_demos: int,
    max_labeled_demos: int,
    init_temperature: float,
) -> SoniDU:
    """Optimize using MIPROv2 (Multiprompt Instruction Proposal Optimizer v2).

    MIPROv2 jointly optimizes prompt instructions and few-shot examples
    using Bayesian optimization.

    Args:
        baseline_nlu: Baseline SoniDU module
        trainset: Training examples
        num_trials: Number of optimization trials
        minibatch_size: Optional minibatch size
        num_candidates: Number of candidate prompts
        max_bootstrapped_demos: Maximum bootstrapped demonstrations
        max_labeled_demos: Maximum labeled demonstrations
        init_temperature: Initial temperature for optimization

    Returns:
        Optimized SoniDU module
    """
    # Calculate optimal parameters if not provided
    if num_candidates is None:
        num_candidates = max(int(num_trials * 1.5), 20)

    if minibatch_size is None:
        if len(trainset) < 50:
            minibatch_size = 10
        elif len(trainset) < 200:
            minibatch_size = 20
        else:
            minibatch_size = 35

    optimizer = MIPROv2(
        metric=intent_accuracy_metric,
        num_candidates=num_candidates,
        init_temperature=init_temperature,
        auto=None,  # Explicitly disable auto to allow manual parameters
    )

    result = optimizer.compile(
        student=baseline_nlu,
        trainset=trainset,
        num_trials=num_trials,
        max_bootstrapped_demos=max_bootstrapped_demos,
        max_labeled_demos=max_labeled_demos,
        minibatch_size=minibatch_size,
    )
    return result  # type: ignore[no-any-return]


def _evaluate_module(module: SoniDU, trainset: list[dspy.Example]) -> float:
    """Evaluate a module on a trainset.

    Args:
        module: SoniDU module to evaluate
        trainset: List of examples to evaluate on

    Returns:
        Average accuracy score (0.0 to 1.0)
    """
    from soni.du.models import DialogueContext

    scores = []
    for example_idx, example in enumerate(trainset):
        try:
            # Extract structured inputs from example
            # Examples should have history and context fields (new format)
            if hasattr(example, "history"):
                history = example.history
            else:
                history = dspy.History(messages=[])

            if hasattr(example, "context"):
                context = example.context
            else:
                context = DialogueContext()

            current_datetime = getattr(example, "current_datetime", "")

            # Call module as function (DSPy best practice - calls __call__() -> forward())
            prediction = module(
                user_message=example.user_message,
                history=history,
                context=context,
                current_datetime=current_datetime,
            )
            score = intent_accuracy_metric(example, prediction)
            scores.append(score)
        except (AttributeError, KeyError, TypeError, ValueError) as e:
            # Errores esperados en evaluación
            logger.warning(f"Error evaluating example {example_idx}: {e}")
            scores.append(0.0)
        except Exception as e:
            # Errores inesperados
            logger.error(
                f"Unexpected error evaluating example {example_idx}: {e}",
                exc_info=True,
            )
            scores.append(0.0)

    return sum(scores) / len(scores) if scores else 0.0


def load_optimized_module(module_path: Path | str) -> SoniDU:
    """Load a previously optimized SoniDU module from disk.

    Args:
        module_path: Path to the saved module JSON file

    Returns:
        Loaded SoniDU module

    Raises:
        FileNotFoundError: If module file doesn't exist
        RuntimeError: If loading fails
    """
    path = Path(module_path)
    if not path.exists():
        raise FileNotFoundError(f"Module file not found: {module_path}")

    try:
        module = SoniDU()
        module.load(str(path))
        return module
    except (FileNotFoundError, OSError, ValueError, AttributeError) as e:
        # Errores esperados al cargar módulo
        raise RuntimeError(f"Failed to load module from {module_path}: {e}") from e
    except Exception as e:
        # Errores inesperados
        logger.error(f"Unexpected error loading module: {e}", exc_info=True)
        raise RuntimeError(f"Failed to load module from {module_path}: {e}") from e
