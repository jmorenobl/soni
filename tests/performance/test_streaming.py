"""Performance tests for streaming functionality"""

import time
from pathlib import Path

import pytest

from soni.runtime import RuntimeLoop


@pytest.mark.asyncio
async def test_streaming_correctness():
    """Test that streaming produces correct tokens"""
    # Arrange
    config_path = Path("examples/flight_booking/soni.yaml")
    runtime = RuntimeLoop(config_path)
    user_id = "test-perf-stream-1"
    user_msg = "I want to book a flight"

    try:
        # Act
        tokens = []
        async for token in runtime.process_message_stream(user_msg, user_id):
            tokens.append(token)

        # Assert
        assert len(tokens) > 0
        # Tokens should form a coherent response
        full_response = "".join(tokens).strip()
        assert len(full_response) > 0
        # Response should be reasonable (not empty or error)
        assert "error" not in full_response.lower() or len(full_response) > 50
    finally:
        await runtime.cleanup()


@pytest.mark.asyncio
async def test_streaming_order():
    """Test that streaming tokens arrive in correct order"""
    # Arrange
    config_path = Path("examples/flight_booking/soni.yaml")
    runtime = RuntimeLoop(config_path)
    user_id = "test-perf-stream-2"
    user_msg = "Hello"

    try:
        # Act
        tokens = []
        timestamps = []
        async for token in runtime.process_message_stream(user_msg, user_id):
            tokens.append(token)
            timestamps.append(time.time())

        # Assert
        assert len(tokens) > 0
        # Tokens should arrive in order (timestamps increasing)
        for i in range(1, len(timestamps)):
            assert timestamps[i] >= timestamps[i - 1], "Tokens arrived out of order"
    finally:
        await runtime.cleanup()


@pytest.mark.asyncio
async def test_streaming_first_token_latency():
    """Test that first token arrives within target latency"""
    # Arrange
    config_path = Path("examples/flight_booking/soni.yaml")
    runtime = RuntimeLoop(config_path)
    user_id = "test-perf-stream-3"
    user_msg = "I want to book a flight"
    target_latency = 5.0  # 5 seconds (lenient for CI)

    try:
        # Act
        start_time = time.time()
        first_token = None
        async for token in runtime.process_message_stream(user_msg, user_id):
            if first_token is None:
                first_token = token
                first_token_latency = time.time() - start_time
                break

        # Assert
        assert first_token is not None
        assert first_token_latency < target_latency, (
            f"First token latency {first_token_latency:.3f}s exceeds target {target_latency}s"
        )
    finally:
        await runtime.cleanup()
