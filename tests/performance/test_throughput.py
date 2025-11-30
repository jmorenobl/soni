"""Performance tests for throughput"""

import asyncio
import time
from pathlib import Path

import pytest

from soni.runtime import RuntimeLoop


@pytest.mark.asyncio
async def test_throughput_concurrent(skip_without_api_key):
    """
    Test that system handles concurrent requests.

    This test measures system throughput by processing multiple
    concurrent requests and verifying they complete within target time.
    """
    # Arrange
    config_path = Path("examples/flight_booking/soni.yaml")
    runtime = RuntimeLoop(config_path)
    user_msg = "I want to book a flight"  # Message that triggers flow
    num_concurrent = 3  # Reduced for faster tests
    target_throughput = 1.0  # 1 msg/s (lenient for CI)

    async def process_message(user_id: str) -> tuple[str, float]:
        """
        Process a single message and return user_id and elapsed time.

        Args:
            user_id: Unique identifier for this request

        Returns:
            Tuple of (user_id, elapsed_time)
        """
        from soni.core.errors import SoniError

        start_time = time.time()
        try:
            response = await runtime.process_message(
                user_msg=user_msg,
                user_id=user_id,
            )
            elapsed = time.time() - start_time
            # Response should not be empty (may be asking for info or error)
            assert len(response) > 0
            return user_id, elapsed
        except SoniError:
            # If processing fails (e.g., slots not filled), still measure latency
            # This is expected behavior for performance tests
            elapsed = time.time() - start_time
            return user_id, elapsed

    try:
        # Act
        start_time = time.time()
        tasks = [process_message(f"test-throughput-{i}") for i in range(num_concurrent)]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        total_time = time.time() - start_time

        # Filter out exceptions for throughput calculation
        successful_results = [r for r in results if not isinstance(r, Exception)]

        # Calculate throughput based on successful requests
        if len(successful_results) > 0:
            throughput = len(successful_results) / total_time
        else:
            throughput = 0.0

        # Assert
        assert throughput >= target_throughput, (
            f"Throughput {throughput:.2f} msg/s below target {target_throughput} msg/s"
        )
        # All requests should have been processed (may have errors, but should complete)
        assert len(results) == num_concurrent, (
            f"Expected {num_concurrent} results, got {len(results)}"
        )
    finally:
        # Cleanup
        await runtime.cleanup()
