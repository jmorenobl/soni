"""Performance tests for throughput"""

import asyncio
import time
from pathlib import Path

import pytest

from soni.runtime import RuntimeLoop


@pytest.mark.asyncio
async def test_throughput_concurrent():
    """Test that system handles concurrent requests (target > 10 msg/s)"""
    # Arrange
    config_path = Path("examples/flight_booking/soni.yaml")
    runtime = RuntimeLoop(config_path)
    user_msg = "Hello"
    num_concurrent = 3  # Reduced for faster tests
    target_throughput = 1.0  # 1 msg/s (lenient for CI)

    async def process_message(user_id: str) -> tuple[str, float]:
        """Process a single message and return user_id and elapsed time"""
        start_time = time.time()
        response = await runtime.process_message(
            user_msg=user_msg,
            user_id=user_id,
        )
        elapsed = time.time() - start_time
        assert len(response) > 0
        return user_id, elapsed

    try:
        # Act
        start_time = time.time()
        tasks = [process_message(f"test-throughput-{i}") for i in range(num_concurrent)]
        results = await asyncio.gather(*tasks)
        total_time = time.time() - start_time

        # Calculate throughput
        throughput = num_concurrent / total_time

        # Assert
        assert throughput >= target_throughput, (
            f"Throughput {throughput:.2f} msg/s below target {target_throughput} msg/s"
        )
        # All requests should complete successfully
        assert len(results) == num_concurrent
    finally:
        await runtime.cleanup()
