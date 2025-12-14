"""Tests for LangGraph runtime"""

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from soni.actions.base import ActionHandler
from soni.core.config import SoniConfig
from soni.core.scope import ScopeManager
from soni.core.state import (
    DialogueState,
    create_empty_state,
    create_initial_state,
    create_runtime_context,
    get_all_slots,
    get_current_flow,
)
from soni.dm.builder import build_graph
from soni.dm.persistence import CheckpointerFactory
from soni.du.modules import SoniDU
from soni.du.normalizer import SlotNormalizer


@pytest.fixture
def sample_config():
    """Load sample configuration for testing with memory backend"""
    config = SoniConfig.from_yaml("examples/flight_booking/soni.yaml")
    # Configure memory backend for tests (faster, better isolation)
    config.settings.persistence.backend = "memory"
    return config


@pytest.fixture
async def setup_test_graph(sample_config):
    """Fixture to setup graph with auto-cleanup"""
    # Setup dependencies
    scope_manager = ScopeManager(config=sample_config)
    normalizer = SlotNormalizer(config=sample_config)
    action_handler = ActionHandler(config=sample_config)
    du = SoniDU()

    context = create_runtime_context(
        config=sample_config,
        scope_manager=scope_manager,
        normalizer=normalizer,
        action_handler=action_handler,
        du=du,
    )

    # Setup checkpointer
    checkpointer, cm = await CheckpointerFactory.create(sample_config.settings.persistence)

    # Build graph
    graph = build_graph(context, checkpointer)

    yield graph, cm, checkpointer, du

    # Cleanup
    if cm:
        await cm.__aexit__(None, None, None)


@pytest.mark.asyncio
async def test_build_graph_structure(setup_test_graph):
    """Test that graph is built with correct structure"""
    graph, _, _, _ = setup_test_graph

    # Assert
    assert graph is not None
    # Verify graph has invoke/ainvoke methods
    assert hasattr(graph, "invoke") or hasattr(graph, "ainvoke")


@pytest.mark.asyncio
async def test_build_graph_with_checkpointer(setup_test_graph):
    """Test that graph includes checkpointer when configured"""
    graph, _, checkpointer, _ = setup_test_graph

    # Assert
    # Graph should be compiled
    assert graph is not None
    assert checkpointer is not None


@pytest.mark.slow
@pytest.mark.asyncio
async def test_execute_linear_flow_basic(setup_test_graph):
    """Test that graph can be invoked with basic state"""
    graph, _, _, du = setup_test_graph

    # Create state as dict (LangGraph format)
    initial_state = {
        "messages": [{"role": "user", "content": "I want to book a flight to Paris"}],
        "slots": {},
        "current_flow": "book_flight",
        "pending_action": None,
        "last_response": "",
        "turn_count": 0,
        "trace": [],
        "metadata": {},
        "flow_slots": {},
        "flow_stack": [],
        "conversation_state": "idle",
        "nlu_result": None,
        "current_step": None,
        "waiting_for_slot": None,
        "current_prompted_slot": None,
        "all_slots_filled": None,
        "action_result": None,
        "digression_depth": 0,
        "last_digression_type": None,
        "user_message": "I want to book a flight to Paris",
    }

    # Mock SoniDU predict
    mock_nlu_result = MagicMock()
    mock_nlu_result.model_dump.return_value = {
        "message_type": "slot_value",
        "command": "book_flight",
        "slots": [{"name": "destination", "value": "Paris"}],
        "confidence": 0.95,
        "reasoning": "User wants to book flight",
        "confirmation_value": None,
    }
    # dspy expects predict to be called
    du.predict = AsyncMock(return_value=mock_nlu_result)

    # Act
    config = {"configurable": {"thread_id": "test_user"}}
    result = await graph.ainvoke(initial_state, config)

    # Assert
    # Verify graph executed without errors
    assert result is not None
    assert isinstance(result, dict)


@pytest.mark.slow
@pytest.mark.asyncio
async def test_state_persistence_basic(sample_config):
    """Test that state can persist between turns"""
    # Custom setup to access dependencies for mocking
    scope_manager = ScopeManager(config=sample_config)
    normalizer = SlotNormalizer(config=sample_config)
    action_handler = ActionHandler(config=sample_config)

    mock_du = AsyncMock()

    # Setup mock return values properly
    mock_result_1 = MagicMock()
    mock_result_1.model_dump.return_value = {
        "message_type": "slot_value",
        "command": "book_flight",
        "slots": [{"name": "destination", "value": "Paris"}],
        "confidence": 0.95,
        "confirmation_value": None,
    }

    mock_result_2 = MagicMock()
    mock_result_2.model_dump.return_value = {
        "message_type": "slot_value",
        "command": "book_flight",
        "slots": [{"name": "origin", "value": "NYC"}],
        "confidence": 0.95,
        "confirmation_value": None,
    }

    # Use side_effect function to handle multiple calls robustly
    async def predict_side_effect(*args, **kwargs):
        # Simple logic: if Paris in message, return result 1, else result 2
        # args[0] is message string usually, or verify signature
        # predict(message, history, context)
        msg = args[0]
        if "Paris" in msg:
            return mock_result_1
        return mock_result_2

    mock_du.predict.side_effect = predict_side_effect

    context = create_runtime_context(
        config=sample_config,
        scope_manager=scope_manager,
        normalizer=normalizer,
        action_handler=action_handler,
        du=mock_du,
    )

    checkpointer, cm = await CheckpointerFactory.create(sample_config.settings.persistence)
    graph = build_graph(context, checkpointer)

    try:
        user_id = "test_user_123"
        initial_state = {
            "messages": [{"role": "user", "content": "I want to go to Paris"}],
            "slots": {},
            "current_flow": "book_flight",
            "pending_action": None,
            "last_response": "",
            "turn_count": 0,
            "trace": [],
            "metadata": {},
            "flow_slots": {},
            "flow_stack": [],
            "conversation_state": "idle",
            "nlu_result": None,
            "user_message": "I want to go to Paris",
            "current_step": None,
            "waiting_for_slot": None,
            "current_prompted_slot": None,
            "all_slots_filled": None,
            "action_result": None,
            "digression_depth": 0,
            "last_digression_type": None,
        }

        config = {"configurable": {"thread_id": user_id}}

        # Act
        # Execute first turn
        result1 = await graph.ainvoke(initial_state, config)

        # Execute second turn
        second_state = {
            "messages": [{"role": "user", "content": "From NYC"}],
            "user_message": "From NYC",
            # Other fields inherited/updated by LangGraph state,
            # just need to provide what changed or is key
        }

        result2 = await graph.ainvoke(second_state, config)

        # Assert
        assert result1 is not None
        assert result2 is not None

    finally:
        if cm:
            await cm.__aexit__(None, None, None)
