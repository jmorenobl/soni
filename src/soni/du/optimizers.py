"""DSPy optimization pipeline for SoniDU modules."""

import logging
import time
from pathlib import Path
from typing import Any

import dspy
from dspy.teleprompt import MIPROv2

from soni.du.metrics import intent_accuracy_metric
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
        optimizer_type: Type of optimizer to use (currently only "MIPROv2")
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
    if optimizer_type != "MIPROv2":
        raise ValueError(f"Unsupported optimizer type: {optimizer_type}")

    # Create baseline module
    baseline_nlu = SoniDU()

    # Evaluate baseline
    print("Evaluating baseline...")
    baseline_start = time.time()
    baseline_score = _evaluate_module(baseline_nlu, trainset)
    baseline_time = time.time() - baseline_start

    print(f"Baseline accuracy: {baseline_score:.2%} (time: {baseline_time:.2f}s)")

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

    # Configure optimizer
    # Note: auto=None is required when passing num_candidates and num_trials
    optimizer = MIPROv2(
        metric=intent_accuracy_metric,
        num_candidates=num_candidates,
        init_temperature=init_temperature,
        auto=None,  # Explicitly disable auto to allow manual num_candidates/num_trials
    )

    # Optimize
    print(f"Optimizing with {optimizer_type} ({num_trials} trials)...")
    optimization_start = time.time()

    try:
        compile_kwargs = {
            "student": baseline_nlu,
            "trainset": trainset,
            "num_trials": num_trials,
            "max_bootstrapped_demos": max_bootstrapped_demos,
            "max_labeled_demos": max_labeled_demos,
            "minibatch_size": minibatch_size,
        }

        optimized_nlu = optimizer.compile(**compile_kwargs)
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
