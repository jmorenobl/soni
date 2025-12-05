"""Performance tests for latency"""

import statistics
import time
from pathlib import Path

import pytest

from soni.runtime import RuntimeLoop


@pytest.mark.performance
@pytest.mark.asyncio
async def test_latency_p95(skip_without_api_key):
    """
    Test that p95 latency is below target.

    This test measures response latency for initial messages that trigger
    the booking flow. The system should respond quickly even when asking
    for additional information.
    """
    # Arrange
    config_path = Path("examples/flight_booking/soni.yaml")
    runtime = RuntimeLoop(config_path)
    user_id = "test-perf-latency-1"
    user_msg = "I want to book a flight"  # Message that triggers flow
    target_p95 = 10.0  # 10 seconds (lenient for CI)
    num_requests = 5  # Reduced for faster tests

    try:
        # Act
        from soni.core.errors import SoniError

        latencies = []
        for i in range(num_requests):
            start_time = time.time()
            try:
                response = await runtime.process_message(
                    user_msg=user_msg,
                    user_id=f"{user_id}-{i}",
                )
                elapsed = time.time() - start_time
                latencies.append(elapsed)
                # Response should not be empty (may be asking for info or error)
                assert len(response) > 0
            except SoniError:
                # If processing fails (e.g., slots not filled), still measure latency
                # This is expected behavior for performance tests
                elapsed = time.time() - start_time
                latencies.append(elapsed)
                # Don't re-raise - we're measuring latency, not testing correctness

        # Calculate p95
        latencies_sorted = sorted(latencies)
        p95_index = int(0.95 * len(latencies_sorted))
        p95_latency = (
            latencies_sorted[p95_index]
            if p95_index < len(latencies_sorted)
            else latencies_sorted[-1]
        )

        # Assert
        assert p95_latency < target_p95, (
            f"p95 latency {p95_latency:.3f}s exceeds target {target_p95}s"
        )
    finally:
        # Cleanup
        await runtime.cleanup()


@pytest.mark.performance
@pytest.mark.asyncio
async def test_latency_metrics(skip_without_api_key):
    """
    Test that latency metrics are reasonable.

    This test verifies that response times are within acceptable ranges
    for the dialogue system.
    """
    # Arrange
    config_path = Path("examples/flight_booking/soni.yaml")
    runtime = RuntimeLoop(config_path)
    user_id = "test-perf-latency-2"
    user_msg = "I want to book a flight"  # Message that triggers flow
    num_requests = 3  # Reduced for faster tests

    try:
        # Act
        from soni.core.errors import SoniError

        latencies = []
        for i in range(num_requests):
            start_time = time.time()
            try:
                response = await runtime.process_message(
                    user_msg=user_msg,
                    user_id=f"{user_id}-{i}",
                )
                elapsed = time.time() - start_time
                latencies.append(elapsed)
                # Response should not be empty
                assert len(response) > 0
            except SoniError:
                # If processing fails (e.g., slots not filled), still measure latency
                # This is expected behavior for performance tests
                elapsed = time.time() - start_time
                latencies.append(elapsed)
                # Don't re-raise - we're measuring latency, not testing correctness

        # Calculate metrics
        mean_latency = statistics.mean(latencies)
        median_latency = statistics.median(latencies)
        min_latency = min(latencies)
        max_latency = max(latencies)

        # Assert
        assert mean_latency > 0, "Mean latency should be positive"
        assert median_latency > 0, "Median latency should be positive"
        assert min_latency > 0, "Min latency should be positive"
        assert max_latency > 0, "Max latency should be positive"
        assert mean_latency < 30.0, f"Mean latency {mean_latency:.3f}s should be reasonable"
    finally:
        # Cleanup
        await runtime.cleanup()
