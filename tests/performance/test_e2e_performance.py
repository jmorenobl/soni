"""Performance tests for end-to-end conversation flows"""

import asyncio
import statistics
import tempfile
import time
from pathlib import Path

import pytest
import yaml

try:
    import psutil
except ImportError:
    psutil = None

from soni.runtime import RuntimeLoop
from tests.conftest import load_test_config

# Conversation flow for E2E testing
# Use messages that match test_e2e_flight_booking_complete_flow which works correctly
# Direct city names work better than "From X" or "To Y" for NLU extraction
E2E_CONVERSATION = [
    "I want to book a flight",
    "New York",  # Origin - direct city name works better than "From Madrid"
    "Los Angeles",  # Destination - direct city name works better than "To Barcelona"
    "Next Friday",  # Date - works reliably for NLU extraction
]


async def run_e2e_conversation(
    runtime: RuntimeLoop,
    user_id: str,
    messages: list[str],
) -> float:
    """
    Run a complete conversation flow and return total latency.

    Args:
        runtime: RuntimeLoop instance
        user_id: Unique user identifier
        messages: List of messages in the conversation

    Returns:
        Total latency in seconds

    Raises:
        Exception: If conversation fails to complete
    """
    start_time = time.time()

    for message in messages:
        # Process each message - let exceptions propagate so test fails if conversation breaks
        await runtime.process_message(user_msg=message, user_id=user_id)

    return time.time() - start_time


@pytest.mark.performance
@pytest.mark.asyncio
async def test_e2e_latency_p95(skip_without_api_key):
    """
    Test that E2E latency p95 is below target.

    This test measures response latency for complete conversation flows.
    The system should respond quickly even for multi-turn conversations.
    """
    # Arrange
    config = load_test_config("examples/flight_booking/soni.yaml")
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        yaml.dump(config.model_dump(), f)
        temp_config_path = f.name

    try:
        runtime = RuntimeLoop(temp_config_path)
        target_p95 = 1.5  # 1.5 seconds target
        num_conversations = 20  # Reduced for faster tests
        # Act
        latencies = []
        for i in range(num_conversations):
            user_id = f"test-e2e-latency-{i}"
            try:
                latency = await run_e2e_conversation(runtime, user_id, E2E_CONVERSATION)
                latencies.append(latency)
            except Exception as e:
                # Log error but continue with other conversations
                # This allows test to measure performance of successful conversations
                pytest.fail(
                    f"Conversation {i} failed: {e}. "
                    f"Performance test requires all conversations to complete successfully."
                )

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
            f"E2E latency p95 {p95_latency:.3f}s exceeds target {target_p95}s"
        )
    finally:
        # Cleanup
        await runtime.cleanup()
        Path(temp_config_path).unlink(missing_ok=True)


@pytest.mark.performance
@pytest.mark.asyncio
async def test_concurrent_throughput(skip_without_api_key):
    """
    Test that concurrent throughput meets target.

    This test measures system throughput by processing multiple
    concurrent conversations and verifying they complete within target time.
    """
    # Arrange
    config = load_test_config("examples/flight_booking/soni.yaml")
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        yaml.dump(config.model_dump(), f)
        temp_config_path = f.name

    try:
        runtime = RuntimeLoop(temp_config_path)
        num_concurrent = 10
        target_throughput = 10.0  # 10 conversations per second

        async def process_conversation(user_id: str) -> float:
            """Process a single conversation and return elapsed time.

            Raises:
                Exception: If conversation fails to complete
            """
            return await run_e2e_conversation(runtime, user_id, E2E_CONVERSATION)

        # Act
        # Act
        start_time = time.time()
        tasks = [process_conversation(f"test-throughput-{i}") for i in range(num_concurrent)]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        total_time = time.time() - start_time

        # Filter out exceptions
        successful_results = [
            r for r in results if not isinstance(r, Exception) and isinstance(r, (int, float))
        ]

        # Calculate throughput based on successful conversations
        if len(successful_results) > 0 and total_time > 0:
            throughput = len(successful_results) / total_time
        else:
            throughput = 0.0

        # Assert
        assert throughput >= target_throughput, (
            f"Throughput {throughput:.2f} conv/s below target {target_throughput} conv/s"
        )
    finally:
        # Cleanup
        await runtime.cleanup()
        Path(temp_config_path).unlink(missing_ok=True)


@pytest.mark.performance
@pytest.mark.asyncio
async def test_memory_usage(skip_without_api_key):
    """
    Test that memory usage is reasonable.

    This test verifies that memory usage doesn't grow excessively
    during multiple conversations.
    """
    if psutil is None:
        pytest.skip("psutil not available")

    # Arrange
    config = load_test_config("examples/flight_booking/soni.yaml")
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        yaml.dump(config.model_dump(), f)
        temp_config_path = f.name

    try:
        runtime = RuntimeLoop(temp_config_path)
        num_conversations = 20  # Reduced for faster tests
        max_memory_increase_mb = 500.0  # Maximum acceptable memory increase
        # Act
        process = psutil.Process()
        initial_memory = process.memory_info().rss / (1024 * 1024)  # MB

        for i in range(num_conversations):
            user_id = f"test-memory-{i}"
            await run_e2e_conversation(runtime, user_id, E2E_CONVERSATION)

        final_memory = process.memory_info().rss / (1024 * 1024)  # MB
        memory_increase = final_memory - initial_memory

        # Assert
        assert memory_increase < max_memory_increase_mb, (
            f"Memory increase {memory_increase:.1f}MB exceeds limit {max_memory_increase_mb}MB"
        )
    finally:
        # Cleanup
        await runtime.cleanup()
        Path(temp_config_path).unlink(missing_ok=True)


@pytest.mark.performance
@pytest.mark.asyncio
async def test_cpu_usage(skip_without_api_key):
    """
    Test that CPU usage is reasonable.

    This test verifies that CPU usage doesn't spike excessively
    during conversations.
    """
    if psutil is None:
        pytest.skip("psutil not available")

    # Arrange
    config = load_test_config("examples/flight_booking/soni.yaml")
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        yaml.dump(config.model_dump(), f)
        temp_config_path = f.name

    try:
        runtime = RuntimeLoop(temp_config_path)
        num_conversations = 10  # Reduced for faster tests
        max_cpu_percent = 200.0  # Maximum acceptable CPU usage (can be >100% on multi-core)
        # Act
        process = psutil.Process()
        cpu_samples = []

        for i in range(num_conversations):
            user_id = f"test-cpu-{i}"
            # Sample CPU before and after conversation
            cpu_before = process.cpu_percent(interval=0.1)
            await run_e2e_conversation(runtime, user_id, E2E_CONVERSATION)
            cpu_after = process.cpu_percent(interval=0.1)
            cpu_samples.append(max(cpu_before, cpu_after))

        max_cpu = max(cpu_samples) if cpu_samples else 0.0
        mean_cpu = statistics.mean(cpu_samples) if cpu_samples else 0.0

        # Assert
        assert max_cpu < max_cpu_percent, (
            f"Max CPU usage {max_cpu:.1f}% exceeds limit {max_cpu_percent}%"
        )
        # Also check that mean CPU is reasonable
        assert mean_cpu < max_cpu_percent, (
            f"Mean CPU usage {mean_cpu:.1f}% exceeds limit {max_cpu_percent}%"
        )
    finally:
        # Cleanup
        await runtime.cleanup()
        Path(temp_config_path).unlink(missing_ok=True)
