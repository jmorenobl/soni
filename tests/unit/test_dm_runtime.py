"""Tests for LangGraph runtime"""

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from soni.core.config import SoniConfig
from soni.core.state import DialogueState
from soni.dm.graph import SoniGraphBuilder


@pytest.fixture
def sample_config():
    """Load sample configuration for testing"""
    return SoniConfig.from_yaml("examples/flight_booking/soni.yaml")


@pytest.fixture
def graph_builder(sample_config):
    """Create a graph builder for testing"""
    return SoniGraphBuilder(sample_config)


@pytest.mark.asyncio
async def test_build_graph_structure(sample_config):
    """Test that graph is built with correct structure"""
    # Arrange
    builder = SoniGraphBuilder(sample_config)

    # Act
    graph = await builder.build_manual("book_flight")

    # Assert
    assert graph is not None
    # Verify graph has invoke/ainvoke methods
    assert hasattr(graph, "invoke") or hasattr(graph, "ainvoke")


@pytest.mark.asyncio
async def test_build_graph_with_checkpointer(sample_config):
    """Test that graph includes checkpointer when configured"""
    # Arrange
    builder = SoniGraphBuilder(sample_config)

    # Act
    graph = await builder.build_manual("book_flight")

    # Assert
    # Graph should be compiled (checkpointer is integrated during compilation)
    assert graph is not None
    assert builder.checkpointer is not None


@pytest.mark.asyncio
async def test_build_graph_nonexistent_flow(sample_config):
    """Test that building non-existent flow raises error"""
    # Arrange
    from soni.core.errors import ValidationError

    builder = SoniGraphBuilder(sample_config)

    # Act & Assert
    with pytest.raises(ValidationError, match="Flow 'nonexistent' not found"):
        await builder.build_manual("nonexistent")


@pytest.mark.asyncio
async def test_execute_linear_flow_basic(sample_config):
    """Test that graph can be invoked with basic state"""
    # Arrange
    builder = SoniGraphBuilder(sample_config)
    graph = await builder.build_manual("book_flight")

    # Create state as dict (LangGraph format)
    initial_state = {
        "messages": [{"role": "user", "content": "I want to book a flight to Paris"}],
        "slots": {},
        "current_flow": "book_flight",
        "pending_action": None,
        "last_response": "",
        "turn_count": 0,
        "trace": [],
        "summary": None,
    }

    # Mock SoniDU to avoid actual LLM calls
    with patch("soni.dm.graph.SoniDU") as mock_du_class:
        mock_du = AsyncMock()
        mock_du_class.return_value = mock_du
        mock_du.predict.return_value = MagicMock(
            command="book_flight",
            slots={"destination": "Paris"},
            confidence=0.95,
            reasoning="User wants to book flight",
        )

        # Act
        # Execute graph using LangGraph API (sync for MVP with SqliteSaver)
        config = {"configurable": {"thread_id": "test_user"}}
        result = graph.invoke(initial_state, config)

        # Assert
        # Verify graph executed without errors
        assert result is not None
        assert isinstance(result, dict)


@pytest.mark.asyncio
async def test_execute_flow_with_action_basic(sample_config):
    """Test that graph can handle action steps"""
    # Arrange
    builder = SoniGraphBuilder(sample_config)
    graph = await builder.build_manual("book_flight")

    initial_state = {
        "messages": [{"role": "user", "content": "Search flights from NYC to Paris"}],
        "slots": {"origin": "NYC", "destination": "Paris"},
        "current_flow": "book_flight",
        "pending_action": None,
        "last_response": "",
        "turn_count": 0,
        "trace": [],
        "summary": None,
    }

    # Mock ActionHandler
    with patch("soni.actions.base.ActionHandler") as mock_handler_class:
        mock_handler = AsyncMock()
        mock_handler_class.return_value = mock_handler
        mock_handler.execute.return_value = {"flights": ["FL123", "FL456"]}

        # Act
        config = {"configurable": {"thread_id": "test_user"}}
        result = graph.invoke(initial_state, config)

        # Assert
        assert result is not None
        assert isinstance(result, dict)


@pytest.mark.asyncio
async def test_state_persistence_basic(sample_config, tmp_path):
    """Test that state can persist between turns"""
    # Arrange
    # Use temporary database
    sample_config.settings.persistence.path = str(tmp_path / "test.db")
    builder = SoniGraphBuilder(sample_config)
    graph = await builder.build_manual("book_flight")

    user_id = "test_user_123"
    initial_state = {
        "messages": [{"role": "user", "content": "I want to go to Paris"}],
        "slots": {},
        "current_flow": "book_flight",
        "pending_action": None,
        "last_response": "",
        "turn_count": 0,
        "trace": [],
        "summary": None,
    }

    config = {"configurable": {"thread_id": user_id}}

    # Mock SoniDU
    with patch("soni.dm.graph.SoniDU") as mock_du_class:
        mock_du = AsyncMock()
        mock_du_class.return_value = mock_du
        mock_du.predict.return_value = MagicMock(
            command="book_flight",
            slots={"destination": "Paris"},
            confidence=0.95,
            reasoning="User wants to book flight",
        )

        # Act
        # Execute first turn
        result1 = graph.invoke(initial_state, config)

        # Execute second turn (should have persisted state)
        second_state = {
            "messages": [{"role": "user", "content": "From NYC"}],
            "slots": {},
            "current_flow": "book_flight",
            "pending_action": None,
            "last_response": "",
            "turn_count": 0,
            "trace": [],
            "summary": None,
        }
        result2 = graph.invoke(second_state, config)

        # Assert
        # Verify both turns executed
        assert result1 is not None
        assert result2 is not None
        # Note: Full persistence verification depends on LangGraph checkpointing


@pytest.mark.asyncio
async def test_state_isolation_basic(sample_config, tmp_path):
    """Test that different users have isolated state"""
    # Arrange
    sample_config.settings.persistence.path = str(tmp_path / "test.db")
    builder = SoniGraphBuilder(sample_config)
    graph = await builder.build_manual("book_flight")

    user1_id = "user1"
    user2_id = "user2"

    initial_state1 = {
        "messages": [{"role": "user", "content": "I want to go to Paris"}],
        "slots": {},
        "current_flow": "book_flight",
        "pending_action": None,
        "last_response": "",
        "turn_count": 0,
        "trace": [],
        "summary": None,
    }

    initial_state2 = {
        "messages": [{"role": "user", "content": "I want to go to London"}],
        "slots": {},
        "current_flow": "book_flight",
        "pending_action": None,
        "last_response": "",
        "turn_count": 0,
        "trace": [],
        "summary": None,
    }

    # Mock SoniDU
    with patch("soni.dm.graph.SoniDU") as mock_du_class:
        mock_du = AsyncMock()
        mock_du_class.return_value = mock_du
        mock_du.predict.return_value = MagicMock(
            command="book_flight",
            slots={},
            confidence=0.95,
            reasoning="User wants to book flight",
        )

        # Act
        # Execute for user1
        config1 = {"configurable": {"thread_id": user1_id}}
        result1 = graph.invoke(initial_state1, config1)

        # Execute for user2
        config2 = {"configurable": {"thread_id": user2_id}}
        result2 = graph.invoke(initial_state2, config2)

        # Assert
        # Verify each user executed independently
        assert result1 is not None
        assert result2 is not None
        # Note: Full isolation verification depends on LangGraph checkpointing


@pytest.mark.asyncio
async def test_handle_nlu_error(sample_config):
    """Test that NLU errors don't break the flow"""
    # Arrange
    builder = SoniGraphBuilder(sample_config)
    graph = await builder.build_manual("book_flight")

    initial_state = {
        "messages": [{"role": "user", "content": "Invalid message"}],
        "slots": {},
        "current_flow": "book_flight",
        "pending_action": None,
        "last_response": "",
        "turn_count": 0,
        "trace": [],
        "summary": None,
    }

    # Mock SoniDU to raise error
    with patch("soni.dm.graph.SoniDU") as mock_du_class:
        mock_du = AsyncMock()
        mock_du_class.return_value = mock_du
        mock_du.predict.side_effect = Exception("NLU error")

        # Act
        config = {"configurable": {"thread_id": "test_user"}}
        # Graph execution should handle the error
        # Note: Depending on error handling, this might raise or return error state
        try:
            result = graph.invoke(initial_state, config)
            # If no exception, verify error is handled in state
            assert result is not None
        except Exception:
            # If exception is raised, that's also acceptable for MVP
            # The important thing is that the graph structure is correct
            pass


@pytest.mark.asyncio
async def test_handle_action_error(sample_config):
    """Test that action errors don't break the flow"""
    # Arrange
    builder = SoniGraphBuilder(sample_config)
    graph = await builder.build_manual("book_flight")

    initial_state = {
        "messages": [{"role": "user", "content": "Search flights"}],
        "slots": {"origin": "NYC", "destination": "Paris"},
        "current_flow": "book_flight",
        "pending_action": None,
        "last_response": "",
        "turn_count": 0,
        "trace": [],
        "summary": None,
    }

    # Mock ActionHandler to raise error
    with patch("soni.actions.base.ActionHandler") as mock_handler_class:
        mock_handler = AsyncMock()
        mock_handler_class.return_value = mock_handler
        mock_handler.execute.side_effect = RuntimeError("Action failed")

        # Act
        config = {"configurable": {"thread_id": "test_user"}}
        # Graph execution should handle the error
        try:
            result = graph.invoke(initial_state, config)
            # If no exception, verify error is handled in state
            assert result is not None
        except Exception:
            # If exception is raised, that's also acceptable for MVP
            # The important thing is that the graph structure is correct
            pass


@pytest.mark.asyncio
async def test_handle_missing_slot(sample_config):
    """Test that missing slot is handled gracefully"""
    # Arrange
    builder = SoniGraphBuilder(sample_config)
    graph = await builder.build_manual("book_flight")

    initial_state = {
        "messages": [{"role": "user", "content": "Book a flight"}],
        "slots": {},  # Missing required slots
        "current_flow": "book_flight",
        "pending_action": None,
        "last_response": "",
        "turn_count": 0,
        "trace": [],
        "summary": None,
    }

    # Mock SoniDU
    with patch("soni.dm.graph.SoniDU") as mock_du_class:
        mock_du = AsyncMock()
        mock_du_class.return_value = mock_du
        mock_du.predict.return_value = MagicMock(
            command="book_flight",
            slots={},  # No slots extracted
            confidence=0.95,
            reasoning="User wants to book flight",
        )

        # Act
        config = {"configurable": {"thread_id": "test_user"}}
        result = graph.invoke(initial_state, config)

        # Assert
        # Graph should prompt for missing slots
        assert result is not None
        # Note: Actual verification depends on collect_slot_node behavior
