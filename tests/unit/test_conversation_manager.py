"""Tests for ConversationManager"""

from unittest.mock import AsyncMock, MagicMock

import pytest

from soni.core.state import (
    DialogueState,
    create_empty_state,
    get_all_slots,
    get_current_flow,
    push_flow,
    set_slot,
)
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
    assert isinstance(state, dict)
    assert get_current_flow(state) == "none"
    assert state["turn_count"] == 0
    mock_graph.aget_state.assert_called_once_with({"configurable": {"thread_id": user_id}})


@pytest.mark.asyncio
async def test_get_or_create_state_loads_existing(conversation_manager, mock_graph):
    """Test get_or_create_state loads existing state"""
    # Arrange
    user_id = "test-user-2"
    # Create a proper state with new schema
    existing_state = create_empty_state()
    existing_state["messages"] = [{"role": "user", "content": "Hello"}]
    existing_state["last_response"] = "Hi there!"
    existing_state["turn_count"] = 1
    push_flow(existing_state, "book_flight")
    set_slot(existing_state, "destination", "Paris")

    mock_snapshot = MagicMock()
    mock_snapshot.values = existing_state
    mock_graph.aget_state.return_value = mock_snapshot

    # Act
    state = await conversation_manager.get_or_create_state(user_id)

    # Assert
    assert isinstance(state, dict)
    assert get_current_flow(state) == "book_flight"
    assert state["turn_count"] == 1
    assert get_all_slots(state) == {"destination": "Paris"}
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
    assert isinstance(state, dict)
    # Should create new state when values are empty
    assert state["turn_count"] == 0


@pytest.mark.asyncio
async def test_get_or_create_state_with_none_snapshot(conversation_manager, mock_graph):
    """Test get_or_create_state handles None snapshot"""
    # Arrange
    user_id = "test-user-4"
    mock_graph.aget_state.return_value = None

    # Act
    state = await conversation_manager.get_or_create_state(user_id)

    # Assert
    assert isinstance(state, dict)
    assert state["turn_count"] == 0


@pytest.mark.asyncio
async def test_save_state(conversation_manager, mock_graph):
    """Test save_state saves state to graph"""
    # Arrange
    user_id = "test-user-5"
    state = create_empty_state()
    state["messages"] = [{"role": "user", "content": "Hello"}]
    state["turn_count"] = 1
    push_flow(state, "greet")
    set_slot(state, "name", "John")

    # Act
    await conversation_manager.save_state(user_id, state)

    # Assert
    mock_graph.aupdate_state.assert_called_once()
    call_args = mock_graph.aupdate_state.call_args
    assert call_args[0][0] == {"configurable": {"thread_id": user_id}}
    assert get_current_flow(call_args[0][1]) == "greet"
    assert call_args[0][1]["turn_count"] == 1


@pytest.mark.asyncio
async def test_save_state_with_empty_state(conversation_manager, mock_graph):
    """Test save_state saves empty state"""
    # Arrange
    user_id = "test-user-6"
    state = create_empty_state()

    # Act
    await conversation_manager.save_state(user_id, state)

    # Assert
    mock_graph.aupdate_state.assert_called_once()
    call_args = mock_graph.aupdate_state.call_args
    assert call_args[0][0] == {"configurable": {"thread_id": user_id}}
    assert get_current_flow(call_args[0][1]) == "none"
    assert call_args[0][1]["turn_count"] == 0


@pytest.mark.asyncio
async def test_get_or_create_state_multiple_users(conversation_manager, mock_graph):
    """Test get_or_create_state handles multiple users independently"""
    # Arrange
    user_id_1 = "user-1"
    user_id_2 = "user-2"

    # Create states with new schema
    state_1 = create_empty_state()
    state_1["turn_count"] = 1
    push_flow(state_1, "flow1")

    state_2 = create_empty_state()
    state_2["turn_count"] = 2
    push_flow(state_2, "flow2")

    mock_snapshot_1 = MagicMock()
    mock_snapshot_1.values = state_1

    mock_snapshot_2 = MagicMock()
    mock_snapshot_2.values = state_2

    # Configure mock to return different snapshots based on user_id
    def side_effect(config):
        if config["configurable"]["thread_id"] == user_id_1:
            return mock_snapshot_1
        else:
            return mock_snapshot_2

    mock_graph.aget_state.side_effect = side_effect

    # Act
    result_1 = await conversation_manager.get_or_create_state(user_id_1)
    result_2 = await conversation_manager.get_or_create_state(user_id_2)

    # Assert
    assert get_current_flow(result_1) == "flow1"
    assert result_1["turn_count"] == 1
    assert get_current_flow(result_2) == "flow2"
    assert result_2["turn_count"] == 2
    assert mock_graph.aget_state.call_count == 2


@pytest.mark.asyncio
async def test_save_state_multiple_users(conversation_manager, mock_graph):
    """Test save_state handles multiple users independently"""
    # Arrange
    user_id_1 = "user-1"
    user_id_2 = "user-2"

    state_1 = create_empty_state()
    state_1["turn_count"] = 1
    push_flow(state_1, "flow1")

    state_2 = create_empty_state()
    state_2["turn_count"] = 2
    push_flow(state_2, "flow2")

    # Act
    await conversation_manager.save_state(user_id_1, state_1)
    await conversation_manager.save_state(user_id_2, state_2)

    # Assert
    assert mock_graph.aupdate_state.call_count == 2
    call_1 = mock_graph.aupdate_state.call_args_list[0]
    call_2 = mock_graph.aupdate_state.call_args_list[1]

    assert call_1[0][0]["configurable"]["thread_id"] == user_id_1
    assert get_current_flow(call_1[0][1]) == "flow1"

    assert call_2[0][0]["configurable"]["thread_id"] == user_id_2
    assert get_current_flow(call_2[0][1]) == "flow2"


@pytest.mark.asyncio
async def test_get_or_create_state_with_complex_state(conversation_manager, mock_graph):
    """Test get_or_create_state loads complex state correctly"""
    # Arrange
    user_id = "test-user-complex"

    # Create complex state with new schema
    complex_state = create_empty_state()
    complex_state["messages"] = [
        {"role": "user", "content": "I want to book a flight"},
        {"role": "assistant", "content": "Where would you like to go?"},
    ]
    complex_state["turn_count"] = 3
    complex_state["last_response"] = "Great! Let me help you with that."
    complex_state["metadata"]["summary"] = "User wants to book a flight from NYC to Paris"
    complex_state["trace"] = [
        {"turn": 1, "intent": "book_flight"},
        {"turn": 2, "slot": "origin"},
    ]

    # Push flow and set slots
    push_flow(complex_state, "book_flight")
    set_slot(complex_state, "origin", "NYC")
    set_slot(complex_state, "destination", "Paris")
    set_slot(complex_state, "date", "2024-12-25")

    mock_snapshot = MagicMock()
    mock_snapshot.values = complex_state
    mock_graph.aget_state.return_value = mock_snapshot

    # Act
    state = await conversation_manager.get_or_create_state(user_id)

    # Assert
    assert isinstance(state, dict)
    assert len(state["messages"]) == 2
    all_slots = get_all_slots(state)
    assert len(all_slots) == 3
    assert state.get("pending_action") is None
    assert len(state["trace"]) == 2


@pytest.mark.asyncio
async def test_save_state_preserves_complex_data(conversation_manager, mock_graph):
    """Test save_state preserves complex state data"""
    # Arrange
    user_id = "test-user-preserve"

    state = create_empty_state()
    state["messages"] = [
        {"role": "user", "content": "Hello"},
        {"role": "assistant", "content": "Hi!"},
    ]
    state["turn_count"] = 5
    state["last_response"] = "Nice to meet you!"
    state["metadata"]["summary"] = "Creating user profile"
    state["trace"] = [{"event": "test"}]

    push_flow(state, "profile")
    set_slot(state, "name", "Alice")
    set_slot(state, "age", "25")

    # Act
    await conversation_manager.save_state(user_id, state)

    # Assert
    call_args = mock_graph.aupdate_state.call_args[0][1]
    assert len(call_args["messages"]) == 2
    all_slots = get_all_slots(call_args)
    assert len(all_slots) == 2
    assert call_args.get("pending_action") is None
    assert len(call_args["trace"]) == 1
    assert call_args["metadata"]["summary"] == "Creating user profile"


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
    state = create_empty_state()

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
    state = create_empty_state()
    mock_graph.aupdate_state.side_effect = Exception("Save error")

    # Act & Assert
    with pytest.raises(Exception, match="Save error"):
        await conversation_manager.save_state(user_id, state)
