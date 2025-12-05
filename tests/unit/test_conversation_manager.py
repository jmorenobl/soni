"""Tests for ConversationManager"""

from unittest.mock import AsyncMock, MagicMock

import pytest

from soni.core.state import DialogueState
from soni.runtime.conversation_manager import ConversationManager


@pytest.fixture
def mock_graph():
    """Create a mock graph for testing"""
    graph = MagicMock()
    graph.aget_state = AsyncMock()
    graph.aupdate_state = AsyncMock()
    return graph


@pytest.fixture
def conversation_manager(mock_graph):
    """Create a ConversationManager with mock graph"""
    return ConversationManager(mock_graph)


@pytest.mark.asyncio
async def test_conversation_manager_initialization(mock_graph):
    """Test ConversationManager initializes with graph"""
    # Act
    manager = ConversationManager(mock_graph)

    # Assert
    assert manager.graph is mock_graph


@pytest.mark.asyncio
async def test_get_or_create_state_creates_new(conversation_manager, mock_graph):
    """Test get_or_create_state creates new state when none exists"""
    # Arrange
    user_id = "test-user-1"
    mock_snapshot = MagicMock()
    mock_snapshot.values = None
    mock_graph.aget_state.return_value = mock_snapshot

    # Act
    state = await conversation_manager.get_or_create_state(user_id)

    # Assert
    assert isinstance(state, DialogueState)
    assert state.current_flow == "none"
    assert state.turn_count == 0
    mock_graph.aget_state.assert_called_once_with({"configurable": {"thread_id": user_id}})


@pytest.mark.asyncio
async def test_get_or_create_state_loads_existing(conversation_manager, mock_graph):
    """Test get_or_create_state loads existing state"""
    # Arrange
    user_id = "test-user-2"
    existing_state_dict = {
        "messages": [{"role": "user", "content": "Hello"}],
        "slots": {"destination": "Paris"},
        "current_flow": "book_flight",
        "turn_count": 1,
        "last_response": "Hi there!",
        "pending_action": None,
        "trace": [],
        "summary": None,
    }
    mock_snapshot = MagicMock()
    mock_snapshot.values = existing_state_dict
    mock_graph.aget_state.return_value = mock_snapshot

    # Act
    state = await conversation_manager.get_or_create_state(user_id)

    # Assert
    assert isinstance(state, DialogueState)
    assert state.current_flow == "book_flight"
    assert state.turn_count == 1
    assert state.slots == {"destination": "Paris"}
    mock_graph.aget_state.assert_called_once_with({"configurable": {"thread_id": user_id}})


@pytest.mark.asyncio
async def test_get_or_create_state_with_empty_snapshot(conversation_manager, mock_graph):
    """Test get_or_create_state handles empty snapshot"""
    # Arrange
    user_id = "test-user-3"
    mock_snapshot = MagicMock()
    mock_snapshot.values = {}
    mock_graph.aget_state.return_value = mock_snapshot

    # Act
    state = await conversation_manager.get_or_create_state(user_id)

    # Assert
    assert isinstance(state, DialogueState)
    # Should create new state when values are empty
    assert state.turn_count == 0


@pytest.mark.asyncio
async def test_get_or_create_state_with_none_snapshot(conversation_manager, mock_graph):
    """Test get_or_create_state handles None snapshot"""
    # Arrange
    user_id = "test-user-4"
    mock_graph.aget_state.return_value = None

    # Act
    state = await conversation_manager.get_or_create_state(user_id)

    # Assert
    assert isinstance(state, DialogueState)
    assert state.turn_count == 0


@pytest.mark.asyncio
async def test_save_state(conversation_manager, mock_graph):
    """Test save_state saves state to graph"""
    # Arrange
    user_id = "test-user-5"
    state = DialogueState(
        messages=[{"role": "user", "content": "Hello"}],
        slots={"name": "John"},
        current_flow="greet",
        turn_count=1,
    )

    # Act
    await conversation_manager.save_state(user_id, state)

    # Assert
    mock_graph.aupdate_state.assert_called_once()
    call_args = mock_graph.aupdate_state.call_args
    assert call_args[0][0] == {"configurable": {"thread_id": user_id}}
    assert call_args[0][1]["current_flow"] == "greet"
    assert call_args[0][1]["turn_count"] == 1


@pytest.mark.asyncio
async def test_save_state_with_empty_state(conversation_manager, mock_graph):
    """Test save_state saves empty state"""
    # Arrange
    user_id = "test-user-6"
    state = DialogueState()

    # Act
    await conversation_manager.save_state(user_id, state)

    # Assert
    mock_graph.aupdate_state.assert_called_once()
    call_args = mock_graph.aupdate_state.call_args
    assert call_args[0][0] == {"configurable": {"thread_id": user_id}}
    assert call_args[0][1]["current_flow"] == "none"
    assert call_args[0][1]["turn_count"] == 0


@pytest.mark.asyncio
async def test_get_or_create_state_multiple_users(conversation_manager, mock_graph):
    """Test get_or_create_state handles multiple users independently"""
    # Arrange
    user_id_1 = "user-1"
    user_id_2 = "user-2"

    mock_snapshot_1 = MagicMock()
    mock_snapshot_1.values = {"current_flow": "flow1", "turn_count": 1}

    mock_snapshot_2 = MagicMock()
    mock_snapshot_2.values = {"current_flow": "flow2", "turn_count": 2}

    # Configure mock to return different snapshots based on user_id
    def side_effect(config):
        if config["configurable"]["thread_id"] == user_id_1:
            return mock_snapshot_1
        else:
            return mock_snapshot_2

    mock_graph.aget_state.side_effect = side_effect

    # Act
    state_1 = await conversation_manager.get_or_create_state(user_id_1)
    state_2 = await conversation_manager.get_or_create_state(user_id_2)

    # Assert
    assert state_1.current_flow == "flow1"
    assert state_1.turn_count == 1
    assert state_2.current_flow == "flow2"
    assert state_2.turn_count == 2
    assert mock_graph.aget_state.call_count == 2


@pytest.mark.asyncio
async def test_save_state_multiple_users(conversation_manager, mock_graph):
    """Test save_state handles multiple users independently"""
    # Arrange
    user_id_1 = "user-1"
    user_id_2 = "user-2"
    state_1 = DialogueState(current_flow="flow1", turn_count=1)
    state_2 = DialogueState(current_flow="flow2", turn_count=2)

    # Act
    await conversation_manager.save_state(user_id_1, state_1)
    await conversation_manager.save_state(user_id_2, state_2)

    # Assert
    assert mock_graph.aupdate_state.call_count == 2
    call_1 = mock_graph.aupdate_state.call_args_list[0]
    call_2 = mock_graph.aupdate_state.call_args_list[1]

    assert call_1[0][0]["configurable"]["thread_id"] == user_id_1
    assert call_1[0][1]["current_flow"] == "flow1"

    assert call_2[0][0]["configurable"]["thread_id"] == user_id_2
    assert call_2[0][1]["current_flow"] == "flow2"


@pytest.mark.asyncio
async def test_get_or_create_state_with_complex_state(conversation_manager, mock_graph):
    """Test get_or_create_state loads complex state correctly"""
    # Arrange
    user_id = "test-user-complex"
    complex_state_dict = {
        "messages": [
            {"role": "user", "content": "I want to book a flight"},
            {"role": "assistant", "content": "Where would you like to go?"},
        ],
        "slots": {"origin": "NYC", "destination": "Paris", "date": "2024-12-25"},
        "current_flow": "book_flight",
        "turn_count": 3,
        "last_response": "Great! Let me help you with that.",
        "pending_action": "search_flights",
        "trace": [
            {"turn": 1, "intent": "book_flight"},
            {"turn": 2, "slot": "origin"},
        ],
        "summary": "User wants to book a flight from NYC to Paris",
    }
    mock_snapshot = MagicMock()
    mock_snapshot.values = complex_state_dict
    mock_graph.aget_state.return_value = mock_snapshot

    # Act
    state = await conversation_manager.get_or_create_state(user_id)

    # Assert
    assert isinstance(state, DialogueState)
    assert len(state.messages) == 2
    assert len(state.slots) == 3
    assert state.pending_action == "search_flights"
    assert len(state.trace) == 2


@pytest.mark.asyncio
async def test_save_state_preserves_complex_data(conversation_manager, mock_graph):
    """Test save_state preserves complex state data"""
    # Arrange
    user_id = "test-user-preserve"
    state = DialogueState(
        messages=[
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi!"},
        ],
        slots={"name": "Alice", "age": "25"},
        current_flow="profile",
        turn_count=5,
        last_response="Nice to meet you!",
        pending_action="create_profile",
        trace=[{"event": "test"}],
        summary="Creating user profile",
    )

    # Act
    await conversation_manager.save_state(user_id, state)

    # Assert
    call_args = mock_graph.aupdate_state.call_args[0][1]
    assert len(call_args["messages"]) == 2
    assert len(call_args["slots"]) == 2
    assert call_args["pending_action"] == "create_profile"
    assert len(call_args["trace"]) == 1
    assert call_args["summary"] == "Creating user profile"


@pytest.mark.asyncio
async def test_get_or_create_state_calls_graph_with_correct_config(
    conversation_manager, mock_graph
):
    """Test get_or_create_state calls graph with correct config format"""
    # Arrange
    user_id = "test-config-format"
    mock_graph.aget_state.return_value = None

    # Act
    await conversation_manager.get_or_create_state(user_id)

    # Assert
    mock_graph.aget_state.assert_called_once()
    call_config = mock_graph.aget_state.call_args[0][0]
    assert "configurable" in call_config
    assert "thread_id" in call_config["configurable"]
    assert call_config["configurable"]["thread_id"] == user_id


@pytest.mark.asyncio
async def test_save_state_calls_graph_with_correct_config(conversation_manager, mock_graph):
    """Test save_state calls graph with correct config format"""
    # Arrange
    user_id = "test-save-config"
    state = DialogueState()

    # Act
    await conversation_manager.save_state(user_id, state)

    # Assert
    mock_graph.aupdate_state.assert_called_once()
    call_config = mock_graph.aupdate_state.call_args[0][0]
    assert "configurable" in call_config
    assert "thread_id" in call_config["configurable"]
    assert call_config["configurable"]["thread_id"] == user_id


@pytest.mark.asyncio
async def test_get_or_create_state_error_handling(conversation_manager, mock_graph):
    """Test get_or_create_state handles graph errors"""
    # Arrange
    user_id = "test-error"
    mock_graph.aget_state.side_effect = Exception("Graph error")

    # Act & Assert
    with pytest.raises(Exception, match="Graph error"):
        await conversation_manager.get_or_create_state(user_id)


@pytest.mark.asyncio
async def test_save_state_error_handling(conversation_manager, mock_graph):
    """Test save_state handles graph errors"""
    # Arrange
    user_id = "test-save-error"
    state = DialogueState()
    mock_graph.aupdate_state.side_effect = Exception("Save error")

    # Act & Assert
    with pytest.raises(Exception, match="Save error"):
        await conversation_manager.save_state(user_id, state)
