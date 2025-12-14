"""DSPy optimization pipeline for SoniDU modules."""

import logging
import time
from pathlib import Path
from typing import Any

import dspy
from dspy.teleprompt import GEPA, MIPROv2

from soni.du.metrics import gepa_feedback_metric, intent_accuracy_metric
from soni.du.models import DialogueContext, MessageType, NLUOutput, SlotAction, SlotValue
from soni.du.modules import SoniDU

logger = logging.getLogger(__name__)


def _inject_format_examples(trainset: list[dspy.Example]) -> list[dspy.Example]:
    """Inject stratified format-guidance examples at the start of trainset.

    These examples ensure the LLM sees at least one example of each message type,
    particularly critical patterns like CONFIRMATION that may be underrepresented
    in optimizer-selected demos.

    CRITICAL: The optimizer (MIPROv2/GEPA) may not select demos from minority
    patterns like CONFIRMATION. By injecting stratified examples, we guarantee
    coverage of all 9 message types in every prompt.

    Args:
        trainset: Domain-specific training examples

    Returns:
        Combined list with stratified format examples prepended
    """
    # Create confirmation context for confirmation examples
    confirmation_context = DialogueContext(
        current_flow="book_flight",
        current_slots={
            "origin": "Madrid",
            "destination": "Barcelona",
            "departure_date": "tomorrow",
        },
        expected_slots=[],
        conversation_state="confirming",
        available_flows={"book_flight": "Book a flight"},
    )

    # Stratified format examples - one or more per message type
    format_examples = [
        # ============================================================
        # SLOT_VALUE - User provides a value for an expected slot
        # ============================================================
        dspy.Example(
            user_message="New York",
            history=dspy.History(messages=[]),
            context=DialogueContext(
                current_flow="book_flight",
                expected_slots=["destination"],
                current_prompted_slot="destination",
                conversation_state="waiting_for_slot",
            ),
            current_datetime="2024-12-11T10:00:00",
            result=NLUOutput(
                message_type=MessageType.SLOT_VALUE,
                command="book_flight",
                slots=[
                    SlotValue(
                        name="destination",
                        value="New York",
                        confidence=0.95,
                        action=SlotAction.PROVIDE,
                    )
                ],
                confidence=0.95,
            ),
        ).with_inputs("user_message", "history", "context", "current_datetime"),
        # ============================================================
        # CONFIRMATION - Positive (user says yes)
        # ============================================================
        dspy.Example(
            user_message="Yes, that's correct",
            history=dspy.History(messages=[]),
            context=confirmation_context,
            current_datetime="2024-12-11T10:00:00",
            result=NLUOutput(
                message_type=MessageType.CONFIRMATION,
                command="book_flight",
                slots=[],
                confidence=0.95,
                confirmation_value=True,
            ),
        ).with_inputs("user_message", "history", "context", "current_datetime"),
        # ============================================================
        # CONFIRMATION - Negative (user says no)
        # ============================================================
        dspy.Example(
            user_message="No, that's not right",
            history=dspy.History(messages=[]),
            context=confirmation_context,
            current_datetime="2024-12-11T10:00:00",
            result=NLUOutput(
                message_type=MessageType.CONFIRMATION,
                command="book_flight",
                slots=[],
                confidence=0.95,
                confirmation_value=False,
            ),
        ).with_inputs("user_message", "history", "context", "current_datetime"),
        # ============================================================
        # CONFIRMATION - Unclear/Ambiguous (critical for max_retries)
        # ============================================================
        dspy.Example(
            user_message="I'm not sure",
            history=dspy.History(messages=[]),
            context=confirmation_context,
            current_datetime="2024-12-11T10:00:00",
            result=NLUOutput(
                message_type=MessageType.CONFIRMATION,
                command="book_flight",
                slots=[],
                confidence=0.6,
                confirmation_value=None,  # None = unclear/ambiguous
            ),
        ).with_inputs("user_message", "history", "context", "current_datetime"),
        # ============================================================
        # CORRECTION - User corrects a previously provided value
        # ============================================================
        dspy.Example(
            user_message="No, I meant Barcelona not Madrid",
            history=dspy.History(messages=[]),
            context=DialogueContext(
                current_flow="book_flight",
                current_slots={"origin": "Madrid"},
                expected_slots=["destination"],
                conversation_state="waiting_for_slot",
            ),
            current_datetime="2024-12-11T10:00:00",
            result=NLUOutput(
                message_type=MessageType.CORRECTION,
                command="book_flight",
                slots=[
                    SlotValue(
                        name="origin",
                        value="Barcelona",
                        confidence=0.95,
                        action=SlotAction.CORRECT,
                        previous_value="Madrid",
                    )
                ],
                confidence=0.95,
            ),
        ).with_inputs("user_message", "history", "context", "current_datetime"),
        # ============================================================
        # MODIFICATION - User proactively requests to change a value
        # ============================================================
        dspy.Example(
            user_message="Can I change the destination to London?",
            history=dspy.History(messages=[]),
            context=DialogueContext(
                current_flow="book_flight",
                current_slots={"origin": "Paris", "destination": "Barcelona"},
                expected_slots=[],
                conversation_state="ready_for_confirmation",
            ),
            current_datetime="2024-12-11T10:00:00",
            result=NLUOutput(
                message_type=MessageType.MODIFICATION,
                command="book_flight",
                slots=[
                    SlotValue(
                        name="destination",
                        value="London",
                        confidence=0.90,
                        action=SlotAction.MODIFY,
                        previous_value="Barcelona",
                    )
                ],
                confidence=0.90,
            ),
        ).with_inputs("user_message", "history", "context", "current_datetime"),
        # ============================================================
        # INTERRUPTION - User wants to switch to a different flow
        # ============================================================
        dspy.Example(
            user_message="Actually, I want to check my booking status",
            history=dspy.History(messages=[]),
            context=DialogueContext(
                current_flow="book_flight",
                available_flows={
                    "book_flight": "Book a flight",
                    "check_booking": "Check booking status",
                },
            ),
            current_datetime="2024-12-11T10:00:00",
            result=NLUOutput(
                message_type=MessageType.INTERRUPTION,
                command="check_booking",
                slots=[],
                confidence=0.90,
            ),
        ).with_inputs("user_message", "history", "context", "current_datetime"),
        # ============================================================
        # CANCELLATION - User wants to cancel/abort current flow
        # ============================================================
        dspy.Example(
            user_message="Never mind, cancel this",
            history=dspy.History(messages=[]),
            context=DialogueContext(
                current_flow="book_flight",
                current_slots={"origin": "Madrid"},
            ),
            current_datetime="2024-12-11T10:00:00",
            result=NLUOutput(
                message_type=MessageType.CANCELLATION,
                command=None,
                slots=[],
                confidence=0.90,
            ),
        ).with_inputs("user_message", "history", "context", "current_datetime"),
        # ============================================================
        # DIGRESSION - User asks question without changing flow
        # ============================================================
        dspy.Example(
            user_message="What is the baggage allowance?",
            history=dspy.History(messages=[]),
            context=DialogueContext(
                current_flow="book_flight",
                current_slots={"origin": "Madrid", "destination": "Barcelona"},
            ),
            current_datetime="2024-12-11T10:00:00",
            result=NLUOutput(
                message_type=MessageType.DIGRESSION,
                command=None,
                slots=[],
                confidence=0.85,
            ),
        ).with_inputs("user_message", "history", "context", "current_datetime"),
        # ============================================================
        # CLARIFICATION - User asks for explanation about current step
        # ============================================================
        dspy.Example(
            user_message="What do you mean by departure date?",
            history=dspy.History(messages=[]),
            context=DialogueContext(
                current_flow="book_flight",
                current_prompted_slot="departure_date",
                expected_slots=["departure_date"],
                conversation_state="waiting_for_slot",
            ),
            current_datetime="2024-12-11T10:00:00",
            result=NLUOutput(
                message_type=MessageType.CLARIFICATION,
                command=None,
                slots=[],
                confidence=0.85,
            ),
        ).with_inputs("user_message", "history", "context", "current_datetime"),
        # ============================================================
        # CONTINUATION - General continuation without specific intent
        # ============================================================
        dspy.Example(
            user_message="Okay, go ahead",
            history=dspy.History(messages=[]),
            context=DialogueContext(
                current_flow="book_flight",
                current_slots={"origin": "Madrid"},
            ),
            current_datetime="2024-12-11T10:00:00",
            result=NLUOutput(
                message_type=MessageType.CONTINUATION,
                command=None,
                slots=[],
                confidence=0.80,
            ),
        ).with_inputs("user_message", "history", "context", "current_datetime"),
    ]

    # Prepend stratified format examples to domain trainset
    return format_examples + list(trainset)


def optimize_soni_du(
    trainset: list[dspy.Example],
    valset: list[dspy.Example] | None = None,
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
        valset: Optional list of dspy.Example instances for validation
        optimizer_type: Type of optimizer to use ("MIPROv2" or "GEPA")
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

    # Create baseline module WITHOUT pre-loaded optimization
    # This ensures we're measuring improvement from a fresh start
    baseline_nlu = SoniDU(load_baseline=False)

    # Inject a few base examples for format guidance (lowercase enums, structure)
    # These teach the LLM the correct output format without domain bias
    trainset = _inject_format_examples(trainset)

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
            optimized_nlu = _optimize_with_gepa(
                baseline_nlu, trainset, valset, num_trials, timeout_seconds
            )
        else:  # MIPROv2
            optimized_nlu = _optimize_with_miprov2(
                baseline_nlu,
                trainset,
                valset,
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
    valset: list[dspy.Example] | None,
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
        valset: Validation examples for evaluation
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
        valset=valset,
    )
    return result  # type: ignore[no-any-return]


def _optimize_with_miprov2(
    baseline_nlu: SoniDU,
    trainset: list[dspy.Example],
    valset: list[dspy.Example] | None,
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
        valset=valset,
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
