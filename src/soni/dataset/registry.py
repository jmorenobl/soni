"""Registry and validation utilities for dataset creation."""

from collections import Counter
from typing import Any

import dspy

from soni.du.models import MessageType


def validate_dataset(examples: list[dspy.Example]) -> dict[str, Any]:
    """Validate a dataset and return statistics.

    Checks:
    - All examples have required fields
    - Examples are properly formatted
    - Distribution of patterns, domains, contexts

    Args:
        examples: List of dspy.Example instances

    Returns:
        Dictionary with validation results and statistics

    Raises:
        ValueError: If validation fails
    """
    if not examples:
        raise ValueError("Dataset is empty")

    patterns_counter: Counter[MessageType] = Counter()
    domains_counter: Counter[str] = Counter()
    contexts_counter: Counter[str] = Counter()
    validation_errors: list[str] = []

    stats: dict[str, Any] = {
        "total_examples": len(examples),
        "patterns": patterns_counter,
        "domains": domains_counter,
        "contexts": contexts_counter,
        "validation_errors": validation_errors,
    }

    for idx, example in enumerate(examples):
        # Check required fields
        required_fields = ["user_message", "history", "context", "result"]
        for field in required_fields:
            if not hasattr(example, field):
                validation_errors.append(f"Example {idx}: missing field '{field}'")

        # Collect statistics
        if hasattr(example, "result"):
            result = example.result
            if hasattr(result, "message_type"):
                patterns_counter[result.message_type] += 1

    # Check distribution balance
    if patterns_counter:
        pattern_counts = list(patterns_counter.values())
        min_count = min(pattern_counts)
        max_count = max(pattern_counts)

        # Warn if imbalanced (max > 3 * min)
        if max_count > 3 * min_count:
            validation_errors.append(
                f"Imbalanced pattern distribution: min={min_count}, max={max_count}"
            )

    if validation_errors:
        raise ValueError(
            f"Dataset validation failed with {len(validation_errors)} errors: "
            f"{validation_errors[:3]}"
        )

    return stats


def print_dataset_stats(examples: list[dspy.Example]) -> None:
    """Print human-readable dataset statistics.

    Args:
        examples: List of dspy.Example instances
    """
    # Collect stats manually to avoid validation errors on expected imbalance
    if not examples:
        print("Dataset is empty")
        return

    patterns_counter: Counter[MessageType] = Counter()
    for ex in examples:
        if hasattr(ex, "result") and hasattr(ex.result, "message_type"):
            patterns_counter[ex.result.message_type] += 1

    print("\n=== Dataset Statistics ===")
    print(f"Total examples: {len(examples)}")
    print("\nPattern distribution:")
    for pattern, count in sorted(patterns_counter.items()):
        percentage = (count / len(examples)) * 100
        print(f"  {pattern}: {count} ({percentage:.1f}%)")
