"""Performance tests for scoping functionality"""

import time
from pathlib import Path

import pytest

from soni.core.config import ConfigLoader, SoniConfig
from soni.core.scope import ScopeManager
from soni.core.state import DialogueState


def count_tokens(text: str) -> int:
    """
    Estimate token count (simple approximation).

    In production, use tiktoken or similar.
    For now, use simple approximation: ~4 characters per token.
    """
    return len(text) // 4


@pytest.mark.asyncio
async def test_scoping_token_reduction():
    """
    Test that scoping reduces tokens by more than 30%.

    This test validates that dynamic scoping significantly reduces
    the number of tokens sent to the LLM by filtering actions.
    """
    # Arrange
    config_path = Path("examples/flight_booking/soni.yaml")
    config_dict = ConfigLoader.load(config_path)
    config = SoniConfig(**config_dict)

    scope_manager = ScopeManager(config=config)

    # Test cases with different dialogue states
    test_cases = [
        {
            "current_flow": "none",
            "slots": {},
        },
        {
            "current_flow": "book_flight",
            "slots": {},
        },
        {
            "current_flow": "book_flight",
            "slots": {"origin": "Madrid"},
        },
        {
            "current_flow": "book_flight",
            "slots": {"origin": "Madrid", "destination": "Barcelona"},
        },
    ]

    # Act - Measure tokens with scoping
    total_tokens_with_scoping = 0
    for test_case in test_cases:
        state = DialogueState(
            current_flow=test_case.get("current_flow", "none"),
            slots=test_case.get("slots", {}),
        )
        scoped_actions = scope_manager.get_available_actions(state)
        actions_str = ", ".join(scoped_actions)
        tokens = count_tokens(actions_str)
        total_tokens_with_scoping += tokens

    avg_tokens_with_scoping = total_tokens_with_scoping / len(test_cases)

    # Act - Measure tokens without scoping (baseline)
    all_actions = list(config.actions.keys()) if hasattr(config, "actions") else []
    all_possible_actions = all_actions.copy()

    # Add all flow start actions
    for flow_name in config.flows.keys():
        all_possible_actions.append(f"start_{flow_name}")

    # Add all slot provide actions
    for slot_name in config.slots.keys():
        all_possible_actions.append(f"provide_{slot_name}")

    # Add global actions
    all_possible_actions.extend(["help", "cancel", "restart"])
    all_possible_actions = list(set(all_possible_actions))

    actions_str = ", ".join(all_possible_actions)
    tokens_without_scoping = count_tokens(actions_str)

    # Calculate reduction
    if tokens_without_scoping > 0:
        token_reduction = (
            (tokens_without_scoping - avg_tokens_with_scoping) / tokens_without_scoping * 100
        )
    else:
        token_reduction = 0.0

    # Assert
    target_reduction = 30.0
    assert token_reduction >= target_reduction, (
        f"Token reduction {token_reduction:.1f}% below target {target_reduction}% "
        f"(with scoping: {avg_tokens_with_scoping:.1f}, without: {tokens_without_scoping:.1f})"
    )


def test_scoping_latency_impact():
    """
    Test that scoping doesn't add significant latency.

    This test verifies that the scoping mechanism is fast enough
    to not impact overall system latency.
    """
    # Arrange
    config_path = Path("examples/flight_booking/soni.yaml")
    config_dict = ConfigLoader.load(config_path)
    config = SoniConfig(**config_dict)

    scope_manager = ScopeManager(config=config)
    state = DialogueState(current_flow="book_flight", slots={"origin": "Madrid"})

    # Act - Measure scoping latency
    num_iterations = 100
    latencies = []

    for _ in range(num_iterations):
        start_time = time.time()
        scope_manager.get_available_actions(state)
        elapsed = time.time() - start_time
        latencies.append(elapsed)

    avg_latency = sum(latencies) / len(latencies)
    max_latency = max(latencies)

    # Assert - Scoping should be very fast (< 10ms average, < 50ms max)
    max_acceptable_avg = 0.01  # 10ms
    max_acceptable_max = 0.05  # 50ms

    assert avg_latency < max_acceptable_avg, (
        f"Average scoping latency {avg_latency * 1000:.2f}ms exceeds limit {max_acceptable_avg * 1000}ms"
    )
    assert max_latency < max_acceptable_max, (
        f"Max scoping latency {max_latency * 1000:.2f}ms exceeds limit {max_acceptable_max * 1000}ms"
    )


def test_scoping_cache_performance():
    """
    Test that scoping cache works correctly and improves performance.

    This test verifies that:
    1. Cache hits are faster than cache misses
    2. Cache returns consistent results
    3. Cache improves performance significantly
    """
    # Arrange
    config_path = Path("examples/flight_booking/soni.yaml")
    config_dict = ConfigLoader.load(config_path)
    config = SoniConfig(**config_dict)

    scope_manager = ScopeManager(config=config)
    state = DialogueState(current_flow="book_flight", slots={"origin": "Madrid"})

    # Act - First call (cache miss)
    start_time = time.time()
    actions1 = scope_manager.get_available_actions(state)
    cache_miss_latency = time.time() - start_time

    # Act - Second call (cache hit)
    start_time = time.time()
    actions2 = scope_manager.get_available_actions(state)
    cache_hit_latency = time.time() - start_time

    # Assert - Cache hit should be faster
    assert cache_hit_latency < cache_miss_latency, (
        f"Cache hit latency {cache_hit_latency * 1000:.2f}ms should be less than "
        f"cache miss latency {cache_miss_latency * 1000:.2f}ms"
    )

    # Assert - Results should be consistent
    assert actions1 == actions2, "Cache should return consistent results"

    # Assert - Cache should provide significant speedup (at least 2x faster)
    speedup = cache_miss_latency / cache_hit_latency if cache_hit_latency > 0 else 0.0
    assert speedup >= 2.0, (
        f"Cache speedup {speedup:.1f}x should be at least 2x "
        f"(miss: {cache_miss_latency * 1000:.2f}ms, hit: {cache_hit_latency * 1000:.2f}ms)"
    )

    # Assert - Cache should be populated
    assert len(scope_manager.scoping_cache) > 0, "Cache should be populated after use"
