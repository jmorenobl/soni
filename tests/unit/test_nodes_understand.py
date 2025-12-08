"""Tests for understand node."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from soni.core.state import create_initial_state
from soni.dm.nodes.understand import understand_node
from soni.du.models import MessageType, NLUOutput


@pytest.mark.asyncio
async def test_understand_node_calls_nlu():
    """Test understand node calls NLU provider."""
    # Arrange
    state = create_initial_state("Hello")

    # Mock runtime context
    # understand_node now uses predict() with structured types
    mock_nlu = AsyncMock()
    mock_nlu.predict.return_value = NLUOutput(
        message_type=MessageType.INTERRUPTION,
        command="greet",
        slots=[],
        confidence=0.9,
        reasoning="greeting",
    )

    mock_flow_manager = MagicMock()
    mock_flow_manager.get_active_context.return_value = None

    mock_scope_manager = MagicMock()
    mock_scope_manager.get_available_actions.return_value = ["greet"]
    mock_scope_manager.get_available_flows.return_value = []

    mock_runtime = MagicMock()
    mock_runtime.context = {
        "du": mock_nlu,  # Changed from "nlu_provider" to "du"
        "flow_manager": mock_flow_manager,
        "scope_manager": mock_scope_manager,
    }

    # Act
    result = await understand_node(state, mock_runtime)

    # Assert
    assert result["conversation_state"] == "understanding"
    assert result["nlu_result"]["command"] == "greet"
    mock_nlu.predict.assert_called_once()
    assert "last_nlu_call" in result


@pytest.mark.asyncio
async def test_understand_node_with_active_flow():
    """Test understand node with active flow context."""
    # Arrange
    state = create_initial_state("I want to book a flight")
    state["flow_stack"] = [
        {
            "flow_id": "flow_1",
            "flow_name": "book_flight",
            "flow_state": "active",
            "current_step": None,
            "outputs": {},
            "started_at": 0.0,
            "paused_at": None,
            "completed_at": None,
            "context": None,
        }
    ]
    state["flow_slots"] = {"flow_1": {"origin": "Madrid"}}

    mock_nlu = AsyncMock()
    from soni.du.models import SlotValue

    mock_nlu.predict.return_value = NLUOutput(
        message_type=MessageType.SLOT_VALUE,
        command="book_flight",
        slots=[SlotValue(name="destination", value="Barcelona", confidence=0.95)],
        confidence=0.95,
        reasoning="destination provided",
    )

    mock_flow_manager = MagicMock()
    mock_flow_manager.get_active_context.return_value = {
        "flow_id": "flow_1",
        "flow_name": "book_flight",
    }

    mock_scope_manager = MagicMock()
    mock_scope_manager.get_available_actions.return_value = ["book_flight"]
    mock_scope_manager.get_available_flows.return_value = ["book_flight"]

    mock_runtime = MagicMock()
    mock_runtime.context = {
        "du": mock_nlu,  # Changed from "nlu_provider" to "du"
        "flow_manager": mock_flow_manager,
        "scope_manager": mock_scope_manager,
    }

    # Act
    result = await understand_node(state, mock_runtime)

    # Assert
    # message_type is serialized as enum value string
    assert result["nlu_result"]["message_type"] == "slot_value"
    # Verify predict was called with structured types
    call_args = mock_nlu.predict.call_args
    assert call_args[0][0] == "I want to book a flight"
    # Second arg is dspy.History, third is DialogueContext
    dialogue_context = call_args[0][2]  # DialogueContext object
    assert dialogue_context.current_flow == "book_flight"
    assert "origin" in dialogue_context.current_slots


@pytest.mark.asyncio
async def test_understand_node_passes_expected_slots():
    """Test understand node passes expected_slots from scope_manager to NLU."""
    # Arrange
    state = create_initial_state("I want to go to Paris")
    state["flow_stack"] = [
        {
            "flow_id": "flow_1",
            "flow_name": "book_flight",
            "flow_state": "active",
            "current_step": None,
            "outputs": {},
            "started_at": 0.0,
            "paused_at": None,
            "completed_at": None,
            "context": None,
        }
    ]

    mock_nlu = AsyncMock()
    from soni.du.models import SlotValue

    mock_nlu.predict.return_value = NLUOutput(
        message_type=MessageType.SLOT_VALUE,
        command="book_flight",
        slots=[SlotValue(name="destination", value="Paris", confidence=0.95)],
        confidence=0.95,
        reasoning="destination provided",
    )

    mock_flow_manager = MagicMock()
    mock_flow_manager.get_active_context.return_value = {
        "flow_id": "flow_1",
        "flow_name": "book_flight",
    }

    mock_scope_manager = MagicMock()
    mock_scope_manager.get_available_actions.return_value = ["book_flight"]
    mock_scope_manager.get_available_flows.return_value = []
    # Mock expected_slots from flow definition
    mock_scope_manager.get_expected_slots.return_value = ["origin", "destination", "departure_date"]

    mock_runtime = MagicMock()
    mock_runtime.context = {
        "du": mock_nlu,  # Changed from "nlu_provider" to "du"
        "flow_manager": mock_flow_manager,
        "scope_manager": mock_scope_manager,
    }

    # Act
    result = await understand_node(state, mock_runtime)

    # Assert
    # message_type is serialized as enum value string
    assert result["nlu_result"]["message_type"] == "slot_value"
    # Verify expected_slots were passed to NLU
    call_args = mock_nlu.predict.call_args
    dialogue_context = call_args[0][2]  # DialogueContext object
    assert dialogue_context.expected_slots == ["origin", "destination", "departure_date"]
    # Verify get_expected_slots was called with correct arguments
    mock_scope_manager.get_expected_slots.assert_called_once_with(
        flow_name="book_flight",
        available_actions=["book_flight"],
    )


@pytest.mark.asyncio
async def test_understand_node_no_expected_slots_when_no_flow():
    """Test understand node passes empty expected_slots when no active flow."""
    # Arrange
    state = create_initial_state("Hello")
    # No flow_stack - no active flow

    mock_nlu = AsyncMock()
    mock_nlu.predict.return_value = NLUOutput(
        message_type=MessageType.INTERRUPTION,
        command="greet",
        slots=[],
        confidence=0.9,
        reasoning="greeting",
    )

    mock_flow_manager = MagicMock()
    mock_flow_manager.get_active_context.return_value = None

    mock_scope_manager = MagicMock()
    mock_scope_manager.get_available_actions.return_value = ["greet"]
    mock_scope_manager.get_available_flows.return_value = ["book_flight", "cancel_booking"]
    # get_expected_slots should NOT be called when no flow is active
    mock_scope_manager.get_expected_slots.return_value = []

    # Mock config for two-stage prediction (needed when no flow active)
    mock_config = MagicMock()
    mock_config.flows = {}  # Empty flows dict - command won't map to any flow

    mock_runtime = MagicMock()
    mock_runtime.context = {
        "du": mock_nlu,  # Changed from "nlu_provider" to "du"
        "flow_manager": mock_flow_manager,
        "scope_manager": mock_scope_manager,
        "config": mock_config,
    }

    # Act
    result = await understand_node(state, mock_runtime)

    # Assert
    assert result["conversation_state"] == "understanding"
    # Verify expected_slots is empty when no flow (two-stage prediction uses empty expected_slots in stage 1)
    # With two-stage prediction, predict() is called at least once
    assert mock_nlu.predict.called
    # First call should have empty expected_slots (stage 1: intent detection)
    call_args = mock_nlu.predict.call_args
    dialogue_context = call_args[0][2]  # DialogueContext object
    assert dialogue_context.expected_slots == []
    # Note: get_expected_slots may be called if command is detected and maps to a flow (stage 2)
    # But in this test, command "greet" won't map to any flow (empty flows dict), so stage 2 won't execute


@pytest.mark.asyncio
async def test_understand_node_serializes_message_type_enum():
    """Test that understand_node properly serializes MessageType enum to string."""
    # Arrange
    from soni.du.models import SlotAction, SlotValue

    state = create_initial_state("I want to book a flight")

    mock_nlu = AsyncMock()
    mock_nlu.predict.return_value = NLUOutput(
        message_type=MessageType.SLOT_VALUE,
        command="test_command",
        slots=[
            SlotValue(
                name="test_slot",
                value="test_value",
                confidence=0.9,
                action=SlotAction.PROVIDE,
            )
        ],
        confidence=0.9,
        reasoning="Test reasoning",
    )

    mock_flow_manager = MagicMock()
    mock_flow_manager.get_active_context.return_value = None

    mock_scope_manager = MagicMock()
    mock_scope_manager.get_available_actions.return_value = ["test_command"]
    mock_scope_manager.get_available_flows.return_value = []

    mock_runtime = MagicMock()
    mock_runtime.context = {
        "du": mock_nlu,
        "flow_manager": mock_flow_manager,
        "scope_manager": mock_scope_manager,
    }

    # Act
    result = await understand_node(state, mock_runtime)

    # Assert
    assert "nlu_result" in result
    assert isinstance(result["nlu_result"]["message_type"], str)
    assert result["nlu_result"]["message_type"] == "slot_value"
    assert isinstance(result["nlu_result"]["slots"][0]["action"], str)
    assert result["nlu_result"]["slots"][0]["action"] == "provide"


def test_nlu_output_model_dump_json_mode():
    """Test that NLUOutput.model_dump(mode='json') serializes enums to strings."""
    from soni.du.models import NLUOutput, SlotAction, SlotValue

    # Arrange
    nlu_output = NLUOutput(
        message_type=MessageType.INTERRUPTION,
        command="book_flight",
        slots=[
            SlotValue(
                name="origin",
                value="Madrid",
                confidence=0.9,
                action=SlotAction.PROVIDE,
            )
        ],
        confidence=0.95,
        reasoning="User wants to book a flight",
    )

    # Act
    result = nlu_output.model_dump(mode="json")

    # Assert - enums are strings, not enum objects or dicts
    assert result["message_type"] == "interruption"
    assert result["slots"][0]["action"] == "provide"
    assert isinstance(result["message_type"], str)
    assert isinstance(result["slots"][0]["action"], str)
