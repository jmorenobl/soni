#!/usr/bin/env python3
"""Script to validate scoping performance impact"""

import asyncio
import json
import logging
from pathlib import Path
from typing import Any

from soni.core.config import ConfigLoader, SoniConfig
from soni.core.scope import ScopeManager
from soni.core.state import DialogueState

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def count_tokens(text: str) -> int:
    """
    Estimate token count (simple approximation).

    In production, use tiktoken or similar.
    For now, use simple approximation: ~4 characters per token.
    """
    return len(text) // 4


async def measure_tokens_with_scoping(
    test_cases: list[dict[str, Any]],
    config: SoniConfig,
) -> dict[str, Any]:
    """Measure token usage with scoping enabled."""
    scope_manager = ScopeManager(config=config)

    total_tokens = 0
    total_actions = 0
    scoped_actions_list = []

    for test_case in test_cases:
        state = DialogueState(
            current_flow=test_case.get("current_flow", "none"),
            slots=test_case.get("slots", {}),
        )

        # Get scoped actions
        scoped_actions = scope_manager.get_available_actions(state)
        scoped_actions_list.append(len(scoped_actions))
        total_actions += len(scoped_actions)

        # Estimate tokens in actions string
        actions_str = ", ".join(scoped_actions)
        tokens = count_tokens(actions_str)
        total_tokens += tokens

    avg_tokens = total_tokens / len(test_cases) if test_cases else 0
    avg_actions = total_actions / len(test_cases) if test_cases else 0

    return {
        "total_tokens": total_tokens,
        "avg_tokens": avg_tokens,
        "avg_actions": avg_actions,
        "scoped_actions_samples": scoped_actions_list,
    }


async def measure_tokens_without_scoping(
    test_cases: list[dict[str, Any]],
    config: SoniConfig,
) -> dict[str, Any]:
    """Measure token usage without scoping (baseline)."""
    # Get all actions from config
    all_actions = list(config.actions.keys()) if hasattr(config, "actions") else []

    # Also include all possible flow start actions and slot provide actions
    # This simulates what would be sent without scoping
    all_possible_actions = all_actions.copy()

    # Add all flow start actions
    for flow_name in config.flows.keys():
        all_possible_actions.append(f"start_{flow_name}")

    # Add all slot provide actions
    for slot_name in config.slots.keys():
        all_possible_actions.append(f"provide_{slot_name}")

    # Add global actions (always available)
    all_possible_actions.extend(["help", "cancel", "restart"])

    # Remove duplicates
    all_possible_actions = list(set(all_possible_actions))

    # Estimate tokens for all actions
    actions_str = ", ".join(all_possible_actions)
    tokens_per_case = count_tokens(actions_str)
    total_tokens = tokens_per_case * len(test_cases)

    return {
        "total_tokens": total_tokens,
        "avg_tokens": tokens_per_case,
        "avg_actions": len(all_possible_actions),
    }


async def measure_accuracy_impact(
    test_cases: list[dict[str, Any]],
    config: SoniConfig,
) -> dict[str, Any]:
    """
    Measure accuracy impact of scoping.

    This is a simplified measurement. In production, would use
    actual NLU predictions and compare results.
    For now, we measure that scoping reduces noise and should improve accuracy.
    """
    scope_manager = ScopeManager(config=config)

    # Simplified: count how many times scoping reduces actions significantly
    # This is a proxy for accuracy improvement
    reduction_count = 0
    total_reduction = 0
    all_actions_count = len(config.actions) if hasattr(config, "actions") else 0

    for test_case in test_cases:
        state = DialogueState(
            current_flow=test_case.get("current_flow", "none"),
            slots=test_case.get("slots", {}),
        )

        scoped_actions = scope_manager.get_available_actions(state)
        scoped_count = len(scoped_actions)

        if all_actions_count > 0:
            reduction = ((all_actions_count - scoped_count) / all_actions_count) * 100
            total_reduction += reduction
            if reduction > 30:  # Significant reduction
                reduction_count += 1

    avg_reduction = total_reduction / len(test_cases) if test_cases else 0

    return {
        "avg_reduction_percent": avg_reduction,
        "significant_reductions": reduction_count,
        "total_cases": len(test_cases),
    }


async def main() -> None:
    """Main validation function."""
    logger.info("Starting scoping performance validation")

    # Load configuration
    config_path = Path("examples/flight_booking/soni.yaml")
    config_dict = ConfigLoader.load(config_path)
    config = SoniConfig(**config_dict)

    # Define test cases
    test_cases = [
        {
            "user_message": "I want to book a flight",
            "current_flow": "none",
            "slots": {},
        },
        {
            "user_message": "From Madrid to Barcelona",
            "current_flow": "book_flight",
            "slots": {},
        },
        {
            "user_message": "On March 15th",
            "current_flow": "book_flight",
            "slots": {"origin": "Madrid", "destination": "Barcelona"},
        },
        {
            "user_message": "Help me",
            "current_flow": "book_flight",
            "slots": {"origin": "Madrid"},
        },
        {
            "user_message": "Cancel my booking",
            "current_flow": "book_flight",
            "slots": {
                "origin": "Madrid",
                "destination": "Barcelona",
                "departure_date": "2024-03-15",
            },
        },
    ]

    logger.info(f"Running validation with {len(test_cases)} test cases")

    # Measure tokens with scoping
    logger.info("Measuring tokens with scoping...")
    tokens_with_scoping = await measure_tokens_with_scoping(test_cases, config)

    # Measure tokens without scoping
    logger.info("Measuring tokens without scoping...")
    tokens_without_scoping = await measure_tokens_without_scoping(test_cases, config)

    # Calculate reduction
    if tokens_without_scoping["avg_tokens"] > 0:
        token_reduction = (
            (tokens_without_scoping["avg_tokens"] - tokens_with_scoping["avg_tokens"])
            / tokens_without_scoping["avg_tokens"]
            * 100
        )
    else:
        token_reduction = 0

    # Measure accuracy impact
    logger.info("Measuring accuracy impact...")
    accuracy_impact = await measure_accuracy_impact(test_cases, config)

    # Compile results
    results = {
        "test_cases_count": len(test_cases),
        "tokens_with_scoping": tokens_with_scoping,
        "tokens_without_scoping": tokens_without_scoping,
        "token_reduction_percent": token_reduction,
        "accuracy_impact": accuracy_impact,
        "objectives": {
            "target_token_reduction": 30.0,
            "target_accuracy_improvement": 5.0,
        },
        "status": {
            "token_reduction_met": token_reduction >= 30.0,
            "accuracy_improvement_estimated": accuracy_impact["avg_reduction_percent"] >= 5.0,
        },
    }

    # Save results
    results_dir = Path("experiments/results")
    results_dir.mkdir(parents=True, exist_ok=True)
    results_path = results_dir / "scoping_performance_results.json"

    with open(results_path, "w") as f:
        json.dump(results, f, indent=2)

    logger.info(f"Results saved to {results_path}")

    # Print summary
    print("\n" + "=" * 60)
    print("SCOPING PERFORMANCE VALIDATION RESULTS")
    print("=" * 60)
    print(f"\nTest Cases: {len(test_cases)}")
    print("\nToken Reduction:")
    print(f"  With Scoping:    {tokens_with_scoping['avg_tokens']:.1f} tokens/case")
    print(f"  Without Scoping: {tokens_without_scoping['avg_tokens']:.1f} tokens/case")
    print(f"  Reduction:       {token_reduction:.1f}%")
    print("  Target:         30.0%")
    print(f"  Status:         {'✓ MET' if token_reduction >= 30.0 else '✗ NOT MET'}")
    print("\nAction Reduction:")
    print(f"  With Scoping:    {tokens_with_scoping['avg_actions']:.1f} actions/case")
    print(f"  Without Scoping: {tokens_without_scoping['avg_actions']:.1f} actions/case")
    print(f"  Average Reduction: {accuracy_impact['avg_reduction_percent']:.1f}%")
    print(f"\nResults saved to: {results_path}")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    asyncio.run(main())
