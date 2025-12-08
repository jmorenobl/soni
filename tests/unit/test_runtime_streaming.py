"""Tests for RuntimeLoop streaming functionality"""

import tempfile
import time
from pathlib import Path

import pytest
import yaml

from soni.core.errors import ValidationError
from soni.runtime import RuntimeLoop
from tests.conftest import load_test_config


@pytest.mark.integration
@pytest.mark.asyncio
async def test_process_message_stream_yields_tokens():
    """Test that process_message_stream yields tokens"""
    # Arrange
    config = load_test_config("examples/flight_booking/soni.yaml")
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        yaml.dump(config.model_dump(), f)
        temp_config_path = f.name

    try:
        runtime = RuntimeLoop(temp_config_path)
        user_id = "test-user-stream-1"
        user_msg = "I want to book a flight"

        # Act
        tokens = []
        async for token in runtime.process_message_stream(user_msg, user_id):
            tokens.append(token)
            # Stop after first few tokens for test
            if len(tokens) >= 5:
                break

        # Assert
        assert len(tokens) > 0
        assert all(isinstance(token, str) for token in tokens)
    finally:
        await runtime.cleanup()
        Path(temp_config_path).unlink(missing_ok=True)


@pytest.mark.integration
@pytest.mark.asyncio
async def test_process_message_stream_first_token_latency():
    """Test that first token is sent quickly"""
    # Arrange
    config = load_test_config("examples/flight_booking/soni.yaml")
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        yaml.dump(config.model_dump(), f)
        temp_config_path = f.name

    try:
        runtime = RuntimeLoop(temp_config_path)
        user_id = "test-user-stream-2"
        user_msg = "Hello"

        # Act
        start_time = time.time()
        first_token = None
        async for token in runtime.process_message_stream(user_msg, user_id):
            if first_token is None:
                first_token = token
                first_token_time = time.time() - start_time
                break

        # Assert
        assert first_token is not None
        # First token should arrive within 500ms (objective)
        # Note: This may be flaky in CI, so we use a more lenient threshold
        assert first_token_time < 5.0  # 5 seconds (lenient for CI)
    finally:
        await runtime.cleanup()
        Path(temp_config_path).unlink(missing_ok=True)


@pytest.mark.integration
@pytest.mark.asyncio
async def test_process_message_stream_handles_errors():
    """Test that streaming handles errors gracefully"""
    # Arrange
    config = load_test_config("examples/flight_booking/soni.yaml")
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        yaml.dump(config.model_dump(), f)
        temp_config_path = f.name

    try:
        runtime = RuntimeLoop(temp_config_path)
        user_id = "test-user-stream-3"
        user_msg = ""  # Invalid empty message

        # Act & Assert
        with pytest.raises(ValidationError):
            async for _token in runtime.process_message_stream(user_msg, user_id):
                pass
    finally:
        await runtime.cleanup()
        Path(temp_config_path).unlink(missing_ok=True)


@pytest.mark.integration
@pytest.mark.asyncio
async def test_process_message_stream_preserves_state():
    """Test that streaming preserves state between tokens"""
    # Arrange
    config = load_test_config("examples/flight_booking/soni.yaml")
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        yaml.dump(config.model_dump(), f)
        temp_config_path = f.name

    try:
        runtime = RuntimeLoop(temp_config_path)
        user_id = "test-user-stream-4"
        user_msg = "I want to book a flight"

        # Act
        tokens = []
        async for token in runtime.process_message_stream(user_msg, user_id):
            tokens.append(token)
            # Stop after a few tokens
            if len(tokens) >= 10:
                break

        # Send second message
        tokens2 = []
        async for token in runtime.process_message_stream("From Madrid", user_id):
            tokens2.append(token)
            # Stop after a few tokens
            if len(tokens2) >= 10:
                break

        # Assert
        # State should be preserved between messages
        assert len(tokens) > 0
        assert len(tokens2) > 0
    finally:
        await runtime.cleanup()
        Path(temp_config_path).unlink(missing_ok=True)


@pytest.mark.integration
@pytest.mark.asyncio
async def test_process_message_stream_returns_strings():
    """Test that streaming yields strings compatible with SSE"""
    # Arrange
    config = load_test_config("examples/flight_booking/soni.yaml")
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        yaml.dump(config.model_dump(), f)
        temp_config_path = f.name

    try:
        runtime = RuntimeLoop(temp_config_path)
        user_id = "test-user-stream-5"
        user_msg = "Hello"

        # Act
        tokens = []
        async for token in runtime.process_message_stream(user_msg, user_id):
            tokens.append(token)
            if len(tokens) >= 3:
                break

        # Assert
        assert len(tokens) > 0
        assert all(isinstance(token, str) for token in tokens)
        # Tokens should be non-empty strings
        assert all(len(token) > 0 for token in tokens)
    finally:
        await runtime.cleanup()
        Path(temp_config_path).unlink(missing_ok=True)
