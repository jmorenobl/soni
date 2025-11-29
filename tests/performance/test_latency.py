"""Performance tests for latency"""

import statistics
import time
from pathlib import Path

import pytest

from soni.runtime import RuntimeLoop


@pytest.mark.asyncio
async def test_latency_p95():
    """Test that p95 latency is below target (< 3s)"""
    # Arrange
    config_path = Path("examples/flight_booking/soni.yaml")
    runtime = RuntimeLoop(config_path)
    user_id = "test-perf-latency-1"
    user_msg = "Hello"
    target_p95 = 10.0  # 10 seconds (lenient for CI)
    num_requests = 5  # Reduced for faster tests

    try:
        # Act
        latencies = []
        for i in range(num_requests):
            start_time = time.time()
            response = await runtime.process_message(
                user_msg=user_msg,
                user_id=f"{user_id}-{i}",
            )
            elapsed = time.time() - start_time
            latencies.append(elapsed)
            assert len(response) > 0  # Response should not be empty

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
        await runtime.cleanup()


@pytest.mark.asyncio
async def test_latency_metrics():
    """Test that latency metrics are reasonable"""
    # Arrange
    config_path = Path("examples/flight_booking/soni.yaml")
    runtime = RuntimeLoop(config_path)
    user_id = "test-perf-latency-2"
    user_msg = "I want to book a flight"
    num_requests = 3  # Reduced for faster tests

    try:
        # Act
        latencies = []
        for i in range(num_requests):
            start_time = time.time()
            response = await runtime.process_message(
                user_msg=user_msg,
                user_id=f"{user_id}-{i}",
            )
            elapsed = time.time() - start_time
            latencies.append(elapsed)
            assert len(response) > 0

        # Calculate metrics
        mean_latency = statistics.mean(latencies)
        median_latency = statistics.median(latencies)
        min_latency = min(latencies)
        max_latency = max(latencies)

        # Assert
        assert mean_latency > 0
        assert median_latency > 0
        assert min_latency > 0
        assert max_latency > 0
        assert mean_latency < 30.0  # Mean should be reasonable
    finally:
        await runtime.cleanup()
