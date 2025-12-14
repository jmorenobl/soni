"""Tests for RuntimeLoop"""

import asyncio
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from soni.core.errors import NLUError, SoniError, ValidationError
from soni.core.interfaces import IActionHandler, INLUProvider, INormalizer, IScopeManager
from soni.runtime import RuntimeLoop


@pytest.mark.asyncio
async def test_runtime_loop_initialization(runtime_loop):
    """Test that RuntimeLoop initializes correctly"""
    # Arrange
    config_path = "examples/flight_booking/soni.yaml"

    # Act
    runtime = await runtime_loop(config_path)
    await runtime._ensure_graph_initialized()

    # Assert
    assert runtime.config is not None
    assert runtime.graph is not None
    assert runtime.du is not None


@pytest.mark.asyncio
async def test_runtime_loop_with_optimized_du(runtime_loop):
    """Test RuntimeLoop with optimized DU module"""
    # Arrange
    config_path = "examples/flight_booking/soni.yaml"

    # Act
    runtime = await runtime_loop(config_path, optimized_du_path=None)

    # Assert
    assert runtime.du is not None


@pytest.mark.asyncio
async def test_process_message_simple(runtime_loop):
    """Test processing a simple message"""
    # Arrange
    config_path = "examples/flight_booking/soni.yaml"
    runtime = await runtime_loop(config_path)
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


@pytest.mark.asyncio
async def test_process_message_empty_message(runtime_loop):
    """Test that empty message raises ValidationError"""
    # Arrange
    config_path = "examples/flight_booking/soni.yaml"
    runtime = await runtime_loop(config_path)
    user_id = "test-user-1"
    user_msg = ""

    # Act & Assert
    with pytest.raises(ValidationError):
        await runtime.process_message(user_msg, user_id)


@pytest.mark.asyncio
async def test_process_message_empty_user_id(runtime_loop):
    """Test that empty user_id raises ValidationError"""
    # Arrange
    config_path = "examples/flight_booking/soni.yaml"
    runtime = await runtime_loop(config_path)
    user_id = ""
    user_msg = "Hello"

    # Act & Assert
    with pytest.raises(ValidationError):
        await runtime.process_message(user_msg, user_id)


@pytest.mark.asyncio
async def test_process_message_multiple_conversations(runtime_loop):
    """Test that multiple conversations are handled independently"""
    # Arrange
    config_path = "examples/flight_booking/soni.yaml"
    runtime = await runtime_loop(config_path)
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


@pytest.mark.asyncio
async def test_process_message_updates_state(runtime_loop):
    """Test that process_message updates state correctly"""
    # Arrange
    config_path = "examples/flight_booking/soni.yaml"
    runtime = await runtime_loop(config_path)
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


@pytest.mark.asyncio
async def test_process_message_handles_nlu_error(runtime_loop):
    """Test that NLU errors are handled correctly"""
    # Arrange
    config_path = "examples/flight_booking/soni.yaml"
    runtime = await runtime_loop(config_path)
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


@pytest.mark.asyncio
async def test_process_message_handles_graph_error(runtime_loop):
    """Test that graph execution errors are handled correctly"""
    # Arrange
    config_path = "examples/flight_booking/soni.yaml"
    runtime = await runtime_loop(config_path)
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


@pytest.mark.asyncio
async def test_runtime_cleanup():
    """Test that RuntimeLoop cleanup closes checkpointer"""
    # Arrange
    import tempfile

    import yaml

    from tests.conftest import load_test_config

    # Load config and configure memory backend for tests
    config = load_test_config("examples/flight_booking/soni.yaml")
    config.settings.persistence.backend = "memory"

    # Create temporary config file with memory backend
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        yaml.dump(config.model_dump(), f)
        temp_config_path = f.name

    try:
        runtime = RuntimeLoop(temp_config_path)

        # Initialize directly using internal method to setup checkpointer
        await runtime._ensure_graph_initialized()

        # Verify checkpointer exists
        assert runtime.checkpointer is not None

        # Act
        await runtime.cleanup()

        # Assert - checkpointer should be None after cleanup
        assert runtime.checkpointer is None
    finally:
        # Cleanup temporary config file
        Path(temp_config_path).unlink(missing_ok=True)


@pytest.mark.asyncio
async def test_runtime_cleanup_called_multiple_times():
    """Test that RuntimeLoop cleanup can be called multiple times safely"""
    # Arrange
    import tempfile

    import yaml

    from tests.conftest import load_test_config

    # Load config and configure memory backend for tests
    config = load_test_config("examples/flight_booking/soni.yaml")
    config.settings.persistence.backend = "memory"

    # Create temporary config file with memory backend
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        yaml.dump(config.model_dump(), f)
        temp_config_path = f.name

    try:
        runtime = RuntimeLoop(temp_config_path)
        await runtime._ensure_graph_initialized()

        # Act
        await runtime.cleanup()
        await runtime.cleanup()  # Should not raise error
    finally:
        # Cleanup temporary config file
        Path(temp_config_path).unlink(missing_ok=True)

    # Assert
    assert runtime.checkpointer is None


@pytest.mark.asyncio
async def test_process_message_with_checkpoint_loading(runtime_loop):
    """Test that process_message loads existing state from checkpoint"""
    # Arrange
    config_path = "examples/flight_booking/soni.yaml"
    runtime = await runtime_loop(config_path)
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
        # StateSnapshot has 'next' attribute (tuple of pending node names)
        # Empty tuple () means no pending tasks (graph not interrupted)
        mock_state_snapshot = type("StateSnapshot", (), {"values": existing_state, "next": ()})()
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
        # aget_state is called 3 times:
        # 1. In _load_or_create_state
        # 2. In _execute_graph before ainvoke (to check if interrupted)
        # 3. In _execute_graph after ainvoke (to check if still interrupted)
        assert mock_aget_state.call_count == 3
        assert response == "Where would you like to go?"


@pytest.mark.asyncio
async def test_process_message_checkpoint_loading_error(runtime_loop):
    """Test that process_message handles checkpoint loading errors gracefully"""
    # Arrange
    config_path = "examples/flight_booking/soni.yaml"
    runtime = await runtime_loop(config_path)
    await runtime._ensure_graph_initialized()
    user_id = "test-user-error"
    user_msg = "Hello"

    # Mock aget_state to raise error
    with (
        patch.object(runtime.graph, "aget_state") as mock_aget_state,
        patch.object(runtime.graph, "ainvoke") as mock_ainvoke,
    ):
        # Mock aget_state to raise expected persistence error (OSError) on first call
        # Second call (in _execute_graph) should return empty snapshot (no pending tasks)
        def side_effect(*args, **kwargs):
            if mock_aget_state.call_count == 1:
                raise OSError("Checkpoint loading failed")
            # Return empty snapshot for subsequent calls
            return type("StateSnapshot", (), {"values": {}, "next": ()})()

        mock_aget_state.side_effect = side_effect

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


@pytest.mark.asyncio
async def test_runtime_loop_dependency_injection(runtime_loop):
    """Test that RuntimeLoop accepts injected dependencies"""
    # Arrange
    config_path = "examples/flight_booking/soni.yaml"

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
    runtime = await runtime_loop(
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


@pytest.mark.asyncio
async def test_runtime_loop_default_dependencies(runtime_loop):
    """Test that RuntimeLoop creates default dependencies when not provided"""
    # Arrange
    from soni.core.scope import ScopeManager
    from soni.du.modules import SoniDU
    from soni.du.normalizer import SlotNormalizer

    config_path = "examples/flight_booking/soni.yaml"

    # Act
    runtime = await runtime_loop(config_path)

    # Assert
    # Should create default implementations
    assert runtime.scope_manager is not None
    assert runtime.normalizer is not None
    assert runtime.du is not None
    # action_handler can be None (not used yet)
    assert isinstance(runtime.scope_manager, ScopeManager)
    assert isinstance(runtime.normalizer, SlotNormalizer)
    assert isinstance(runtime.du, SoniDU)


# === _validate_inputs ===


@pytest.mark.asyncio
async def test_validate_inputs_success(runtime_loop):
    """Test _validate_inputs with valid inputs."""
    config_path = "examples/flight_booking/soni.yaml"
    runtime = await runtime_loop(config_path)

    sanitized_msg, sanitized_user_id = runtime._validate_inputs("Hello", "user123")

    assert sanitized_msg == "Hello"
    assert sanitized_user_id == "user123"


@pytest.mark.asyncio
async def test_validate_inputs_sanitizes(runtime_loop):
    """Test _validate_inputs sanitizes inputs."""
    config_path = "examples/flight_booking/soni.yaml"
    runtime = await runtime_loop(config_path)

    sanitized_msg, sanitized_user_id = runtime._validate_inputs("  Hello  ", "  user123  ")

    assert sanitized_msg == "Hello"
    assert sanitized_user_id == "user123"


@pytest.mark.asyncio
async def test_validate_inputs_empty_message(runtime_loop):
    """Test _validate_inputs raises ValidationError for empty message."""
    config_path = "examples/flight_booking/soni.yaml"
    runtime = await runtime_loop(config_path)

    with pytest.raises(ValidationError, match="Message cannot be empty"):
        runtime._validate_inputs("", "user123")


@pytest.mark.asyncio
async def test_validate_inputs_empty_user_id(runtime_loop):
    """Test _validate_inputs raises ValidationError for empty user_id."""
    config_path = "examples/flight_booking/soni.yaml"
    runtime = await runtime_loop(config_path)

    with pytest.raises(ValidationError, match="User ID cannot be empty"):
        runtime._validate_inputs("Hello", "")


# === _load_or_create_state ===


@pytest.mark.asyncio
async def test_load_or_create_state_new_state(runtime_loop):
    """Test _load_or_create_state creates new state when none exists."""
    config_path = "examples/flight_booking/soni.yaml"
    runtime = await runtime_loop(config_path)
    await runtime._ensure_graph_initialized()

    with patch.object(runtime.graph, "aget_state") as mock_aget_state:
        # Return empty snapshot (no existing state)
        mock_aget_state.return_value = type("StateSnapshot", (), {"values": {}, "next": ()})()

        state = await runtime._load_or_create_state("new_user", "Hello")

        assert state["user_message"] == "Hello"
        # create_initial_state should add user message
        assert "messages" in state


@pytest.mark.asyncio
async def test_load_or_create_state_loads_existing(runtime_loop):
    """Test _load_or_create_state loads existing state."""
    config_path = "examples/flight_booking/soni.yaml"
    runtime = await runtime_loop(config_path)
    await runtime._ensure_graph_initialized()

    existing_state = {
        "messages": [{"role": "user", "content": "Previous"}],
        "flow_stack": [],
        "turn_count": 1,
    }

    with patch.object(runtime.graph, "aget_state") as mock_aget_state:
        mock_aget_state.return_value = type(
            "StateSnapshot", (), {"values": existing_state, "next": ()}
        )()

        state = await runtime._load_or_create_state("existing_user", "New message")

        assert state["user_message"] == "New message"
        assert len(state["messages"]) > 1  # Should have previous + new


@pytest.mark.asyncio
async def test_load_or_create_state_handles_persistence_error(runtime_loop):
    """Test _load_or_create_state handles persistence errors gracefully."""
    config_path = "examples/flight_booking/soni.yaml"
    runtime = await runtime_loop(config_path)
    await runtime._ensure_graph_initialized()

    with patch.object(runtime.graph, "aget_state") as mock_aget_state:
        from soni.core.errors import PersistenceError

        mock_aget_state.side_effect = PersistenceError("Checkpoint error")

        # Should create new state instead of failing
        state = await runtime._load_or_create_state("error_user", "Hello")

        assert state["user_message"] == "Hello"


# === _execute_graph ===


@pytest.mark.asyncio
async def test_execute_graph_new_conversation(runtime_loop):
    """Test _execute_graph with new conversation."""
    config_path = "examples/flight_booking/soni.yaml"
    runtime = await runtime_loop(config_path)
    await runtime._ensure_graph_initialized()

    from soni.core.state import create_initial_state

    state = create_initial_state("Hello")

    with (
        patch.object(runtime.graph, "aget_state") as mock_aget_state,
        patch.object(runtime.graph, "ainvoke") as mock_ainvoke,
    ):
        # No pending tasks (new conversation)
        mock_aget_state.return_value = type("StateSnapshot", (), {"values": {}, "next": ()})()
        mock_ainvoke.return_value = {"last_response": "Hi there!"}

        result = await runtime._execute_graph(state, "user123")

        assert result["last_response"] == "Hi there!"
        # Should call ainvoke with state dict (not Command)
        assert mock_ainvoke.call_count == 1


@pytest.mark.asyncio
async def test_execute_graph_resumes_interrupted(runtime_loop):
    """Test _execute_graph resumes interrupted conversation."""
    config_path = "examples/flight_booking/soni.yaml"
    runtime = await runtime_loop(config_path)
    await runtime._ensure_graph_initialized()

    from soni.core.state import create_initial_state

    state = create_initial_state("Hello")

    with (
        patch.object(runtime.graph, "aget_state") as mock_aget_state,
        patch.object(runtime.graph, "ainvoke") as mock_ainvoke,
    ):
        # Graph is interrupted (has pending tasks)
        mock_aget_state.side_effect = [
            type("StateSnapshot", (), {"values": {}, "next": ("collect_next_slot",)})(),
            type("StateSnapshot", (), {"values": {}, "next": ()})(),  # After execution
        ]
        mock_ainvoke.return_value = {"last_response": "What is your destination?"}

        result = await runtime._execute_graph(state, "user123")

        assert result["last_response"] == "What is your destination?"
        # Should call ainvoke with Command(resume=...) for interrupted graph
        assert mock_ainvoke.call_count == 1


@pytest.mark.asyncio
async def test_execute_graph_processes_interrupts(runtime_loop):
    """Test _execute_graph processes interrupts when graph is still interrupted."""
    config_path = "examples/flight_booking/soni.yaml"
    runtime = await runtime_loop(config_path)
    await runtime._ensure_graph_initialized()

    from soni.core.state import create_initial_state

    state = create_initial_state("Hello")

    with (
        patch.object(runtime.graph, "aget_state") as mock_aget_state,
        patch.object(runtime.graph, "ainvoke") as mock_ainvoke,
    ):
        # Graph is still interrupted after execution
        mock_aget_state.side_effect = [
            type("StateSnapshot", (), {"values": {}, "next": ()})(),  # Before
            type("StateSnapshot", (), {"values": {}, "next": ("collect_next_slot",)})(),  # After
        ]
        # Result has interrupt but no last_response
        # Interrupt format: list of interrupt objects with .value attribute
        interrupt_obj = type("Interrupt", (), {"value": "What is your origin?"})()
        mock_ainvoke.return_value = {"__interrupt__": [interrupt_obj]}

        result = await runtime._execute_graph(state, "user123")

        # Should process interrupts and extract prompt
        assert result["last_response"] == "What is your origin?"


@pytest.mark.asyncio
async def test_execute_graph_extracts_prompt_from_interrupt(runtime_loop):
    """Test _execute_graph extracts prompt from interrupt when graph is interrupted."""
    config_path = "examples/flight_booking/soni.yaml"
    runtime = await runtime_loop(config_path)
    await runtime._ensure_graph_initialized()

    from soni.core.state import create_initial_state

    state = create_initial_state("Hello")

    with (
        patch.object(runtime.graph, "aget_state") as mock_aget_state,
        patch.object(runtime.graph, "ainvoke") as mock_ainvoke,
    ):
        mock_aget_state.side_effect = [
            type("StateSnapshot", (), {"values": {}, "next": ()})(),
            type("StateSnapshot", (), {"values": {}, "next": ("collect_next_slot",)})(),
        ]
        # Result has interrupt with prompt (LangGraph format: list of Interrupt objects)
        mock_ainvoke.return_value = {
            "__interrupt__": [type("Interrupt", (), {"value": "What is your origin?"})()],
            "last_response": "Old response from previous turn",
        }

        result = await runtime._execute_graph(state, "user123")

        # Should extract prompt from interrupt (new behavior after fix)
        assert result["last_response"] == "What is your origin?"


# === _extract_response ===


@pytest.mark.asyncio
async def test_extract_response_from_last_response(runtime_loop):
    """Test _extract_response extracts from last_response."""
    config_path = "examples/flight_booking/soni.yaml"
    runtime = await runtime_loop(config_path)

    result = {"last_response": "Hello, how can I help?"}

    response = runtime._extract_response(result, "user123")

    assert response == "Hello, how can I help?"


@pytest.mark.asyncio
async def test_extract_response_fallback_when_missing(runtime_loop):
    """Test _extract_response uses fallback when last_response missing."""
    config_path = "examples/flight_booking/soni.yaml"
    runtime = await runtime_loop(config_path)

    result = {}  # No last_response

    response = runtime._extract_response(result, "user123")

    # Should return fallback message
    assert isinstance(response, str)
    assert len(response) > 0


# === _process_interrupts ===


@pytest.mark.asyncio
async def test_process_interrupts_extracts_prompt(runtime_loop):
    """Test _process_interrupts extracts prompt from interrupt."""
    config_path = "examples/flight_booking/soni.yaml"
    runtime = await runtime_loop(config_path)

    # Interrupt format: list of interrupt objects with .value attribute
    interrupt_obj = type("Interrupt", (), {"value": "What is your destination?"})()
    result = {"__interrupt__": [interrupt_obj]}

    runtime._process_interrupts(result)

    assert result["last_response"] == "What is your destination?"


@pytest.mark.asyncio
async def test_process_interrupts_no_interrupt(runtime_loop):
    """Test _process_interrupts handles missing interrupt gracefully."""
    config_path = "examples/flight_booking/soni.yaml"
    runtime = await runtime_loop(config_path)

    result = {}  # No interrupt

    runtime._process_interrupts(result)

    # Should not raise error
    assert "last_response" not in result or result.get("last_response") is None


# === process_message_stream ===


@pytest.mark.asyncio
async def test_process_message_stream_basic(runtime_loop):
    """Test process_message_stream yields tokens."""
    config_path = "examples/flight_booking/soni.yaml"
    runtime = await runtime_loop(config_path)
    await runtime._ensure_graph_initialized()

    with (
        patch.object(runtime.conversation_manager, "get_or_create_state") as mock_get_state,
        patch.object(runtime.streaming_manager, "stream_response") as mock_stream,
    ):
        from soni.core.state import create_initial_state

        # Mock state loading
        mock_get_state.return_value = create_initial_state("Hello")

        # Mock streaming events - format matches what process_message_stream expects
        async def mock_stream_response(*args, **kwargs):
            # Event format: dict with node names as keys
            yield {"generate_response": {"last_response": "Hello there!"}}

        mock_stream.return_value = mock_stream_response()

        tokens = []
        async for token in runtime.process_message_stream("Hello", "user123"):
            tokens.append(token)

        assert len(tokens) > 0


# === Edge Cases ===


@pytest.mark.asyncio
async def test_process_message_none_message(runtime_loop):
    """Test process_message handles None message."""
    config_path = "examples/flight_booking/soni.yaml"
    runtime = await runtime_loop(config_path)
    user_id = "test-user-1"
    user_msg = None

    # Act & Assert
    with pytest.raises((ValidationError, TypeError)):
        await runtime.process_message(user_msg, user_id)


@pytest.mark.asyncio
async def test_ensure_graph_initialized_concurrent(runtime_loop):
    """Test _ensure_graph_initialized handles concurrent calls safely."""
    config_path = "examples/flight_booking/soni.yaml"
    runtime = await runtime_loop(config_path)

    # Call multiple times concurrently
    await asyncio.gather(
        runtime._ensure_graph_initialized(),
        runtime._ensure_graph_initialized(),
        runtime._ensure_graph_initialized(),
    )

    # Graph should be initialized (only once due to lock)
    assert runtime.graph is not None
    # Verify lock was used (graph should exist after concurrent calls)
    assert hasattr(runtime, "_graph_init_lock")
