"""Tests for StreamingManager"""

from unittest.mock import AsyncMock, MagicMock

import pytest

from soni.core.state import DialogueState
from soni.runtime.streaming_manager import StreamingManager


@pytest.fixture
def mock_graph():
    """Create a mock graph for testing"""
    graph = MagicMock()
    graph.astream = AsyncMock()
    return graph


@pytest.fixture
def streaming_manager():
    """Create a StreamingManager instance"""
    return StreamingManager()


@pytest.mark.asyncio
async def test_stream_response_basic(streaming_manager, mock_graph):
    """Test stream_response yields events from graph"""
    # Arrange
    user_id = "test-user-1"
    state = DialogueState(current_flow="test_flow", turn_count=1)

    # Mock graph.astream to yield events
    async def mock_astream(*args, **kwargs):
        yield {"event": "start"}
        yield {"event": "processing"}
        yield {"event": "end"}

    mock_graph.astream = mock_astream

    # Act
    events = []
    async for event in streaming_manager.stream_response(mock_graph, state, user_id):
        events.append(event)

    # Assert
    assert len(events) == 3
    assert events[0] == {"event": "start"}
    assert events[1] == {"event": "processing"}
    assert events[2] == {"event": "end"}


@pytest.mark.asyncio
async def test_stream_response_with_empty_state(streaming_manager, mock_graph):
    """Test stream_response with empty state"""
    # Arrange
    user_id = "test-user-2"
    state = DialogueState()

    async def mock_astream(*args, **kwargs):
        yield {"event": "test"}

    mock_graph.astream = mock_astream

    # Act
    events = []
    async for event in streaming_manager.stream_response(mock_graph, state, user_id):
        events.append(event)

    # Assert
    assert len(events) == 1
    assert events[0] == {"event": "test"}


@pytest.mark.asyncio
async def test_stream_response_calls_graph_with_correct_params(streaming_manager, mock_graph):
    """Test stream_response calls graph.astream with correct parameters"""
    # Arrange
    user_id = "test-user-3"
    state = DialogueState(current_flow="book_flight", slots={"destination": "Paris"}, turn_count=2)

    call_args = []

    async def mock_astream(*args, **kwargs):
        call_args.append((args, kwargs))
        yield {"event": "test"}

    mock_graph.astream = mock_astream

    # Act
    async for _ in streaming_manager.stream_response(mock_graph, state, user_id):
        pass

    # Assert
    assert len(call_args) == 1
    args, kwargs = call_args[0]

    # Check state dict was passed
    assert args[0]["current_flow"] == "book_flight"
    assert args[0]["slots"] == {"destination": "Paris"}
    assert args[0]["turn_count"] == 2

    # Check config
    assert kwargs["config"] == {"configurable": {"thread_id": user_id}}
    assert kwargs["stream_mode"] == "updates"


@pytest.mark.asyncio
async def test_stream_response_with_complex_state(streaming_manager, mock_graph):
    """Test stream_response handles complex state"""
    # Arrange
    user_id = "test-user-4"
    state = DialogueState(
        messages=[
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi!"},
        ],
        slots={"name": "Alice", "age": "25"},
        current_flow="profile",
        turn_count=3,
        last_response="Nice to meet you!",
        pending_action="save_profile",
    )

    async def mock_astream(*args, **kwargs):
        yield {"node": "collect_slot", "data": {"slot": "name"}}
        yield {"node": "execute_action", "data": {"action": "save_profile"}}

    mock_graph.astream = mock_astream

    # Act
    events = []
    async for event in streaming_manager.stream_response(mock_graph, state, user_id):
        events.append(event)

    # Assert
    assert len(events) == 2
    assert events[0]["node"] == "collect_slot"
    assert events[1]["node"] == "execute_action"


@pytest.mark.asyncio
async def test_stream_response_no_events(streaming_manager, mock_graph):
    """Test stream_response handles no events"""
    # Arrange
    user_id = "test-user-5"
    state = DialogueState()

    async def mock_astream(*args, **kwargs):
        # Yield nothing
        return
        yield  # Make this a generator

    mock_graph.astream = mock_astream

    # Act
    events = []
    async for event in streaming_manager.stream_response(mock_graph, state, user_id):
        events.append(event)

    # Assert
    assert len(events) == 0


@pytest.mark.asyncio
async def test_stream_response_multiple_users(streaming_manager, mock_graph):
    """Test stream_response handles multiple users independently"""
    # Arrange
    user_id_1 = "user-1"
    user_id_2 = "user-2"
    state_1 = DialogueState(current_flow="flow1")
    state_2 = DialogueState(current_flow="flow2")

    calls = []

    async def mock_astream(state_dict, **kwargs):
        calls.append((state_dict, kwargs))
        yield {"user": kwargs["config"]["configurable"]["thread_id"]}

    mock_graph.astream = mock_astream

    # Act
    events_1 = []
    async for event in streaming_manager.stream_response(mock_graph, state_1, user_id_1):
        events_1.append(event)

    events_2 = []
    async for event in streaming_manager.stream_response(mock_graph, state_2, user_id_2):
        events_2.append(event)

    # Assert
    assert len(calls) == 2
    assert calls[0][1]["config"]["configurable"]["thread_id"] == user_id_1
    assert calls[1][1]["config"]["configurable"]["thread_id"] == user_id_2
    assert events_1[0]["user"] == user_id_1
    assert events_2[0]["user"] == user_id_2


@pytest.mark.asyncio
async def test_stream_response_preserves_event_order(streaming_manager, mock_graph):
    """Test stream_response preserves event order"""
    # Arrange
    user_id = "test-user-6"
    state = DialogueState()

    async def mock_astream(*args, **kwargs):
        for i in range(10):
            yield {"sequence": i}

    mock_graph.astream = mock_astream

    # Act
    events = []
    async for event in streaming_manager.stream_response(mock_graph, state, user_id):
        events.append(event)

    # Assert
    assert len(events) == 10
    for i in range(10):
        assert events[i]["sequence"] == i


@pytest.mark.asyncio
async def test_stream_response_error_handling(streaming_manager, mock_graph):
    """Test stream_response handles errors from graph"""
    # Arrange
    user_id = "test-user-7"
    state = DialogueState()

    async def mock_astream(*args, **kwargs):
        yield {"event": "start"}
        raise Exception("Stream error")

    mock_graph.astream = mock_astream

    # Act & Assert
    events = []
    with pytest.raises(Exception, match="Stream error"):
        async for event in streaming_manager.stream_response(mock_graph, state, user_id):
            events.append(event)

    # Should have received event before error
    assert len(events) == 1
    assert events[0] == {"event": "start"}


@pytest.mark.asyncio
async def test_stream_response_converts_state_to_dict(streaming_manager, mock_graph):
    """Test stream_response converts DialogueState to dict"""
    # Arrange
    user_id = "test-user-8"
    state = DialogueState(current_flow="test", turn_count=5)

    received_state = None

    async def mock_astream(state_dict, **kwargs):
        nonlocal received_state
        received_state = state_dict
        yield {"event": "test"}

    mock_graph.astream = mock_astream

    # Act
    async for _ in streaming_manager.stream_response(mock_graph, state, user_id):
        pass

    # Assert
    assert received_state is not None
    assert isinstance(received_state, dict)
    assert received_state["current_flow"] == "test"
    assert received_state["turn_count"] == 5


@pytest.mark.asyncio
async def test_stream_response_uses_updates_mode(streaming_manager, mock_graph):
    """Test stream_response uses 'updates' stream mode"""
    # Arrange
    user_id = "test-user-9"
    state = DialogueState()

    received_kwargs = None

    async def mock_astream(*args, **kwargs):
        nonlocal received_kwargs
        received_kwargs = kwargs
        yield {"event": "test"}

    mock_graph.astream = mock_astream

    # Act
    async for _ in streaming_manager.stream_response(mock_graph, state, user_id):
        pass

    # Assert
    assert received_kwargs is not None
    assert received_kwargs["stream_mode"] == "updates"


@pytest.mark.asyncio
async def test_stream_response_with_different_user_ids(streaming_manager, mock_graph):
    """Test stream_response handles different user ID formats"""
    # Arrange
    test_user_ids = [
        "simple-user",
        "user@example.com",
        "user-123-456",
        "UUID-LIKE-STRING-HERE",
    ]
    state = DialogueState()

    for user_id in test_user_ids:
        received_config = None

        async def mock_astream(*args, **kwargs):
            nonlocal received_config
            received_config = kwargs["config"]
            yield {"event": "test"}

        mock_graph.astream = mock_astream

        # Act
        async for _ in streaming_manager.stream_response(mock_graph, state, user_id):
            pass

        # Assert
        assert received_config["configurable"]["thread_id"] == user_id


@pytest.mark.asyncio
async def test_stream_response_large_number_of_events(streaming_manager, mock_graph):
    """Test stream_response handles large number of events"""
    # Arrange
    user_id = "test-user-10"
    state = DialogueState()
    event_count = 1000

    async def mock_astream(*args, **kwargs):
        for i in range(event_count):
            yield {"event_number": i}

    mock_graph.astream = mock_astream

    # Act
    events = []
    async for event in streaming_manager.stream_response(mock_graph, state, user_id):
        events.append(event)

    # Assert
    assert len(events) == event_count
    assert events[0]["event_number"] == 0
    assert events[-1]["event_number"] == event_count - 1


@pytest.mark.asyncio
async def test_stream_response_is_async_generator(streaming_manager, mock_graph):
    """Test stream_response returns an async generator"""
    # Arrange
    user_id = "test-user-11"
    state = DialogueState()

    async def mock_astream(*args, **kwargs):
        yield {"event": "test"}

    mock_graph.astream = mock_astream

    # Act
    result = streaming_manager.stream_response(mock_graph, state, user_id)

    # Assert
    assert hasattr(result, "__anext__")
    assert hasattr(result, "__aiter__")

    # Consume the generator
    async for _ in result:
        pass
