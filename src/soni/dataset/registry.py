"""Registry and validation utilities for dataset creation."""

from collections import Counter
from typing import Any

import dspy


def validate_dataset(examples: list[dspy.Example]) -> dict[str, Any]:
    """Validate a dataset and return statistics.

    Checks:
    - All examples have required fields
    - Examples are properly formatted
    - Distribution of commands
    """
    if not examples:
        raise ValueError("Dataset is empty")

    commands_counter: Counter[str] = Counter()
    validation_errors: list[str] = []

    stats: dict[str, Any] = {
        "total_examples": len(examples),
        "commands": commands_counter,
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
            if hasattr(result, "commands") and result.commands:
                for cmd in result.commands:
                    commands_counter[cmd.__class__.__name__] += 1
            else:
                # It might be empty commands (e.g. ChitChat without hinted command?)
                # or legacy.
                pass

    # Check distribution (skip balance check for now as commands vary widely)

    if validation_errors:
        raise ValueError(
            f"Dataset validation failed with {len(validation_errors)} errors: "
            f"{validation_errors[:3]}"
        )

    return stats


def print_dataset_stats(examples: list[dspy.Example]) -> None:
    """Print human-readable dataset statistics."""
    # Collect stats manually
    if not examples:
        print("Dataset is empty")
        return

    commands_counter: Counter[str] = Counter()
    for ex in examples:
        if hasattr(ex, "result") and hasattr(ex.result, "commands"):
            for cmd in ex.result.commands:
                commands_counter[cmd.__class__.__name__] += 1

    print("\n=== Dataset Statistics ===")
    print(f"Total examples: {len(examples)}")
    print("\nCommand distribution:")
    for cmd_name, count in sorted(commands_counter.items()):
        # Percentage is based on total COMMANDS, not total examples
        total_cmds = sum(commands_counter.values())
        percentage = (count / total_cmds) * 100 if total_cmds > 0 else 0
        print(f"  {cmd_name}: {count} ({percentage:.1f}%)")
