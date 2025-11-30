"""Tests for RuntimeLoop"""

from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from soni.core.errors import NLUError, SoniError, ValidationError
from soni.core.interfaces import IActionHandler, INLUProvider, INormalizer, IScopeManager
from soni.runtime import RuntimeLoop


@pytest.mark.asyncio
async def test_runtime_loop_initialization():
    """Test that RuntimeLoop initializes correctly"""
    # Arrange
    config_path = Path("examples/flight_booking/soni.yaml")

    # Act
    runtime = RuntimeLoop(config_path)
    try:
        # Initialize graph (lazy initialization)
        await runtime._ensure_graph_initialized()

        # Assert
        assert runtime.config is not None
        assert runtime.graph is not None
        assert runtime.du is not None
    finally:
        await runtime.cleanup()


@pytest.mark.asyncio
async def test_runtime_loop_with_optimized_du():
    """Test RuntimeLoop with optimized DU module"""
    # Arrange
    config_path = Path("examples/flight_booking/soni.yaml")
    # Note: optimized_du_path would need to exist for this test

    # Act
    runtime = RuntimeLoop(config_path, optimized_du_path=None)  # Use None for MVP
    try:
        # Assert
        assert runtime.du is not None
    finally:
        await runtime.cleanup()


@pytest.mark.asyncio
async def test_process_message_simple():
    """Test processing a simple message"""
    # Arrange
    config_path = Path("examples/flight_booking/soni.yaml")
    runtime = RuntimeLoop(config_path)
    try:
        # Initialize graph (lazy initialization)
        await runtime._ensure_graph_initialized()
        user_id = "test-user-1"
        user_msg = "I want to book a flight"

        # Mock graph execution
        with patch.object(runtime.graph, "ainvoke") as mock_ainvoke:
            mock_ainvoke.return_value = {
                "last_response": "Where would you like to go?",
                "current_flow": "book_flight",
                "slots": {},
            }

            # Act
            response = await runtime.process_message(user_msg, user_id)

            # Assert
            assert isinstance(response, str)
            assert len(response) > 0
            assert response == "Where would you like to go?"
    finally:
        await runtime.cleanup()


@pytest.mark.asyncio
async def test_process_message_empty_message():
    """Test that empty message raises ValidationError"""
    # Arrange
    config_path = Path("examples/flight_booking/soni.yaml")
    runtime = RuntimeLoop(config_path)
    try:
        user_id = "test-user-1"
        user_msg = ""

        # Act & Assert
        with pytest.raises(ValidationError):
            await runtime.process_message(user_msg, user_id)
    finally:
        await runtime.cleanup()


@pytest.mark.asyncio
async def test_process_message_empty_user_id():
    """Test that empty user_id raises ValidationError"""
    # Arrange
    config_path = Path("examples/flight_booking/soni.yaml")
    runtime = RuntimeLoop(config_path)
    try:
        user_id = ""
        user_msg = "Hello"

        # Act & Assert
        with pytest.raises(ValidationError):
            await runtime.process_message(user_msg, user_id)
    finally:
        await runtime.cleanup()


@pytest.mark.asyncio
async def test_process_message_multiple_conversations():
    """Test that multiple conversations are handled independently"""
    # Arrange
    config_path = Path("examples/flight_booking/soni.yaml")
    runtime = RuntimeLoop(config_path)
    try:
        # Initialize graph (lazy initialization)
        await runtime._ensure_graph_initialized()
        user_id_1 = "test-user-1"
        user_id_2 = "test-user-2"
        user_msg = "Hello"

        # Mock graph execution
        with patch.object(runtime.graph, "ainvoke") as mock_ainvoke:
            mock_ainvoke.return_value = {
                "last_response": "Hi there!",
                "current_flow": "none",
                "slots": {},
            }

            # Act
            response_1 = await runtime.process_message(user_msg, user_id_1)
            response_2 = await runtime.process_message(user_msg, user_id_2)

            # Assert
            assert isinstance(response_1, str)
            assert isinstance(response_2, str)
            # Each user should have independent state
            assert mock_ainvoke.call_count == 2
    finally:
        await runtime.cleanup()


@pytest.mark.asyncio
async def test_process_message_updates_state():
    """Test that process_message updates state correctly"""
    # Arrange
    config_path = Path("examples/flight_booking/soni.yaml")
    runtime = RuntimeLoop(config_path)
    try:
        # Initialize graph (lazy initialization)
        await runtime._ensure_graph_initialized()
        user_id = "test-user-1"
        user_msg = "I want to book a flight"

        # Mock graph execution
        with patch.object(runtime.graph, "ainvoke") as mock_ainvoke:
            mock_ainvoke.return_value = {
                "last_response": "Where would you like to go?",
                "current_flow": "book_flight",
                "slots": {},
            }

            # Act
            response = await runtime.process_message(user_msg, user_id)

            # Assert
            assert response == "Where would you like to go?"
            mock_ainvoke.assert_called_once()
    finally:
        await runtime.cleanup()


@pytest.mark.asyncio
async def test_process_message_handles_nlu_error():
    """Test that NLU errors are handled correctly"""
    # Arrange
    config_path = Path("examples/flight_booking/soni.yaml")
    runtime = RuntimeLoop(config_path)
    try:
        # Initialize graph (lazy initialization)
        await runtime._ensure_graph_initialized()
        user_id = "test-user-1"
        user_msg = "Invalid message"

        # Mock graph to raise NLUError
        # Note: RuntimeLoop now re-raises NLUError directly (not wrapped)
        with patch.object(runtime.graph, "ainvoke") as mock_ainvoke:
            mock_ainvoke.side_effect = NLUError("Failed to understand message")

            # Act & Assert
            # RuntimeLoop re-raises NLUError directly
            with pytest.raises(NLUError) as exc_info:
                await runtime.process_message(user_msg, user_id)

            assert "Failed to understand message" in str(exc_info.value)
    finally:
        await runtime.cleanup()


@pytest.mark.asyncio
async def test_process_message_handles_graph_error():
    """Test that graph execution errors are handled correctly"""
    # Arrange
    config_path = Path("examples/flight_booking/soni.yaml")
    runtime = RuntimeLoop(config_path)
    try:
        # Initialize graph (lazy initialization)
        await runtime._ensure_graph_initialized()
        user_id = "test-user-1"
        user_msg = "Hello"

        # Mock graph to raise generic error
        with patch.object(runtime.graph, "ainvoke") as mock_ainvoke:
            mock_ainvoke.side_effect = Exception("Graph execution failed")

            # Act & Assert
            with pytest.raises(SoniError) as exc_info:
                await runtime.process_message(user_msg, user_id)

            assert "Failed to process message" in str(exc_info.value)
    finally:
        await runtime.cleanup()


@pytest.mark.asyncio
async def test_runtime_cleanup():
    """Test that RuntimeLoop cleanup calls builder cleanup"""
    # Arrange
    config_path = Path("examples/flight_booking/soni.yaml")
    runtime = RuntimeLoop(config_path)

    # Initialize checkpointer (lazy initialization)
    await runtime.builder.initialize()

    # Verify builder exists
    assert runtime.builder is not None
    assert runtime.builder.checkpointer is not None

    # Act
    await runtime.cleanup()

    # Assert - builder's checkpointer should be closed
    assert runtime.builder.checkpointer is None


@pytest.mark.asyncio
async def test_runtime_cleanup_called_multiple_times():
    """Test that RuntimeLoop cleanup can be called multiple times safely"""
    # Arrange
    config_path = Path("examples/flight_booking/soni.yaml")
    runtime = RuntimeLoop(config_path)

    # Act
    await runtime.cleanup()
    await runtime.cleanup()  # Should not raise error

    # Assert
    assert runtime.builder.checkpointer is None


@pytest.mark.asyncio
async def test_process_message_with_checkpoint_loading():
    """Test that process_message loads existing state from checkpoint"""
    # Arrange
    config_path = Path("examples/flight_booking/soni.yaml")
    runtime = RuntimeLoop(config_path)
    try:
        # Initialize graph (lazy initialization)
        await runtime._ensure_graph_initialized()
        user_id = "test-user-checkpoint"
        user_msg = "I want to book a flight"

        # Mock get_state to return existing state
        existing_state = {
            "messages": [{"role": "user", "content": "Previous message"}],
            "slots": {"origin": "NYC"},
            "current_flow": "book_flight",
            "turn_count": 1,
        }

        with (
            patch.object(runtime.graph, "aget_state") as mock_aget_state,
            patch.object(runtime.graph, "ainvoke") as mock_ainvoke,
        ):
            # Mock aget_state to return existing state
            mock_state_snapshot = type("StateSnapshot", (), {"values": existing_state})()
            mock_aget_state.return_value = mock_state_snapshot

            # Mock ainvoke to return response
            mock_ainvoke.return_value = {
                "last_response": "Where would you like to go?",
                "current_flow": "book_flight",
                "slots": {"origin": "NYC"},
            }

            # Act
            response = await runtime.process_message(user_msg, user_id)

            # Assert
            mock_aget_state.assert_called_once()
            assert response == "Where would you like to go?"
    finally:
        await runtime.cleanup()


@pytest.mark.asyncio
async def test_process_message_checkpoint_loading_error():
    """Test that process_message handles checkpoint loading errors gracefully"""
    # Arrange
    config_path = Path("examples/flight_booking/soni.yaml")
    runtime = RuntimeLoop(config_path)
    try:
        # Initialize graph (lazy initialization)
        await runtime._ensure_graph_initialized()
        user_id = "test-user-error"
        user_msg = "Hello"

        # Mock aget_state to raise error
        with (
            patch.object(runtime.graph, "aget_state") as mock_aget_state,
            patch.object(runtime.graph, "ainvoke") as mock_ainvoke,
        ):
            # Mock aget_state to raise expected persistence error (OSError)
            # This should be caught and handled gracefully (create new state)
            mock_aget_state.side_effect = OSError("Checkpoint loading failed")

            # Mock ainvoke to return response
            mock_ainvoke.return_value = {
                "last_response": "Hello!",
                "current_flow": "none",
                "slots": {},
            }

            # Act - should create new state instead of failing
            response = await runtime.process_message(user_msg, user_id)

            # Assert
            assert response == "Hello!"
    finally:
        await runtime.cleanup()


@pytest.mark.asyncio
async def test_runtime_loop_dependency_injection():
    """Test that RuntimeLoop accepts injected dependencies"""
    # Arrange
    config_path = Path("examples/flight_booking/soni.yaml")

    # Create mock implementations
    mock_scope_manager = MagicMock(spec=IScopeManager)
    mock_scope_manager.get_available_actions.return_value = ["action1", "action2"]

    mock_normalizer = MagicMock(spec=INormalizer)
    mock_normalizer.normalize = AsyncMock(return_value="normalized_value")

    mock_nlu_provider = MagicMock(spec=INLUProvider)
    mock_nlu_provider.predict = AsyncMock(
        return_value={
            "structured_command": "test",
            "extracted_slots": {},
            "confidence": 0.9,
            "reasoning": "test",
        }
    )

    mock_action_handler = MagicMock(spec=IActionHandler)
    mock_action_handler.execute = AsyncMock(return_value={"result": "test"})

    # Act
    runtime = RuntimeLoop(
        config_path,
        scope_manager=mock_scope_manager,
        normalizer=mock_normalizer,
        nlu_provider=mock_nlu_provider,
        action_handler=mock_action_handler,
    )

    # Assert
    assert runtime.scope_manager is mock_scope_manager
    assert runtime.normalizer is mock_normalizer
    assert runtime.du is mock_nlu_provider
    assert runtime.action_handler is mock_action_handler
    # Cleanup
    await runtime.cleanup()


@pytest.mark.asyncio
async def test_runtime_loop_default_dependencies():
    """Test that RuntimeLoop creates default dependencies when not provided"""
    # Arrange
    config_path = Path("examples/flight_booking/soni.yaml")

    # Act
    runtime = RuntimeLoop(config_path)

    # Assert
    # Should create default implementations
    assert runtime.scope_manager is not None
    assert runtime.normalizer is not None
    assert runtime.du is not None
    # action_handler can be None (not used yet)
    from soni.core.scope import ScopeManager
    from soni.du.modules import SoniDU
    from soni.du.normalizer import SlotNormalizer

    assert isinstance(runtime.scope_manager, ScopeManager)
    assert isinstance(runtime.normalizer, SlotNormalizer)
    assert isinstance(runtime.du, SoniDU)
    # Cleanup
    await runtime.cleanup()
