#!/usr/bin/env python
"""Analyze NLU failure patterns to identify systematic issues.

This script evaluates the NLU on the full dataset and identifies:
1. Which examples fail
2. What patterns of failure exist
3. Root causes of misclassification
"""

from collections import defaultdict
from dataclasses import dataclass

import dspy
from soni.dataset import DatasetBuilder
from soni.du.models import DialogueContext, NLUOutput
from soni.du.modules import SoniDU


@dataclass
class FailureCase:
    """Represents a failed prediction."""

    example_index: int
    user_message: str
    expected_type: str
    predicted_type: str
    expected_command: str | None
    predicted_command: str | None
    expected_confirmation: bool | None
    predicted_confirmation: bool | None
    current_flow: str
    score: float


def evaluate_dataset():
    """Evaluate all examples and collect failure cases."""
    # Load optimized module
    nlu = SoniDU(load_baseline=True)

    # Build dataset
    builder = DatasetBuilder()
    examples = builder.build_all(examples_per_combination=3)

    failures: list[FailureCase] = []
    successes = 0
    total = len(examples)

    print(f"\n{'=' * 70}")
    print("EVALUATING NLU ON FULL DATASET")
    print(f"{'=' * 70}")
    print(f"Total examples: {total}\n")

    for i, example in enumerate(examples):
        # Get prediction
        try:
            # Get fields from example - use dict access since dspy.Example is dict-like
            user_message = example.user_message
            history = example.history  # Already a dspy.History
            context = example.context  # Already a DialogueContext
            expected: NLUOutput = example.result  # Expected output
            current_datetime = getattr(example, "current_datetime", "")

            # Get prediction using module call
            prediction = nlu(
                user_message=user_message,
                history=history,
                context=context,
                current_datetime=current_datetime,
            )

            # Extract NLUOutput from prediction
            predicted_output: NLUOutput = prediction.result

            # Compare key fields
            exp_type = expected.message_type.value
            pred_type = predicted_output.message_type.value

            exp_cmd = expected.command
            pred_cmd = predicted_output.command

            exp_conf = expected.confirmation_value
            pred_conf = predicted_output.confirmation_value

            # Score the prediction
            score = 0.0
            if exp_type == pred_type:
                score += 0.5
            if exp_cmd == pred_cmd:
                score += 0.3
            if exp_conf == pred_conf:
                score += 0.2

            current_flow = context.current_flow

            if score < 1.0:
                failures.append(
                    FailureCase(
                        example_index=i,
                        user_message=user_message,
                        expected_type=exp_type,
                        predicted_type=pred_type,
                        expected_command=exp_cmd,
                        predicted_command=pred_cmd,
                        expected_confirmation=exp_conf,
                        predicted_confirmation=pred_conf,
                        current_flow=current_flow,
                        score=score,
                    )
                )
            else:
                successes += 1

            # Progress indicator
            if (i + 1) % 30 == 0:
                print(f"  Progress: {i + 1}/{total} ({100 * (i + 1) / total:.0f}%)")

        except Exception as e:
            print(f"Error on example {i}: {e}")
            import traceback

            traceback.print_exc()
            break

    return failures, successes, total


def analyze_failures(failures: list[FailureCase]):
    """Analyze failure patterns."""
    print(f"\n{'=' * 70}")
    print("FAILURE ANALYSIS")
    print(f"{'=' * 70}\n")

    # Group by failure type
    type_mismatches = defaultdict(list)
    cmd_mismatches = defaultdict(list)
    conf_mismatches = []

    for f in failures:
        if f.expected_type != f.predicted_type:
            key = f"{f.expected_type} → {f.predicted_type}"
            type_mismatches[key].append(f)

        if f.expected_command != f.predicted_command and f.expected_type == f.predicted_type:
            key = f"{f.expected_command} → {f.predicted_command}"
            cmd_mismatches[key].append(f)

        if (
            f.expected_confirmation != f.predicted_confirmation
            and f.expected_type == f.predicted_type
        ):
            conf_mismatches.append(f)

    # Print type mismatches
    print("📊 MESSAGE TYPE MISCLASSIFICATIONS:")
    print("-" * 50)
    if not type_mismatches:
        print("  None!")
    for pattern, cases in sorted(type_mismatches.items(), key=lambda x: -len(x[1])):
        print(f"\n{pattern}: {len(cases)} cases")
        for case in cases[:3]:  # Show first 3
            msg = (
                case.user_message[:60] + "..." if len(case.user_message) > 60 else case.user_message
            )
            print(f'  • "{msg}"')
            print(f"    Flow: {case.current_flow}")

    # Print command mismatches
    if cmd_mismatches:
        print("\n\n📊 COMMAND MISMATCHES (type correct):")
        print("-" * 50)
        for pattern, cases in sorted(cmd_mismatches.items(), key=lambda x: -len(x[1])):
            print(f"\n{pattern}: {len(cases)} cases")
            for case in cases[:2]:
                msg = (
                    case.user_message[:60] + "..."
                    if len(case.user_message) > 60
                    else case.user_message
                )
                print(f'  • "{msg}"')

    # Print confirmation mismatches
    if conf_mismatches:
        print("\n\n📊 CONFIRMATION_VALUE MISMATCHES:")
        print("-" * 50)
        for case in conf_mismatches[:10]:
            print(f'  • "{case.user_message}"')
            print(f"    Expected: {case.expected_confirmation}, Got: {case.predicted_confirmation}")


def main():
    """Run the analysis."""
    # Configure DSPy
    lm = dspy.LM("openai/gpt-4o-mini", max_tokens=1024)
    dspy.configure(lm=lm)

    failures, successes, total = evaluate_dataset()

    print(f"\n{'=' * 70}")
    print("SUMMARY")
    print(f"{'=' * 70}")
    print(f"Total: {total}")
    print(f"Successes: {successes} ({100 * successes / total:.1f}%)")
    print(f"Failures: {len(failures)} ({100 * len(failures) / total:.1f}%)")

    if failures:
        analyze_failures(failures)


if __name__ == "__main__":
    main()
