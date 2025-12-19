from unittest.mock import AsyncMock, Mock

import pytest
from langchain_core.messages import AIMessage
from langchain_core.runnables import RunnableConfig

from soni.config import (
    CancellationPatternConfig,
    ClarificationPatternConfig,
    CorrectionPatternConfig,
    HumanHandoffPatternConfig,
    PatternBehaviorsConfig,
    SettingsConfig,
    SlotConfig,
    SoniConfig,
)
from soni.core.commands import (
    CancelFlow,
    CorrectSlot,
    HumanHandoff,
    RequestClarification,
)
from soni.core.constants import FlowState
from soni.core.types import DialogueState, RuntimeContext
from soni.dm.nodes.understand import understand_node
from soni.du.models import NLUOutput


@pytest.fixture
def mock_runtime_context():
    # Mocks
    mock_du = Mock()
    mock_du.acall = AsyncMock()

    mock_flow_manager = Mock()
    # Now synchronous - returns None (no delta) for mocking simplicity
    mock_flow_manager.set_slot = Mock(return_value=None)
    mock_flow_manager.pop_flow = Mock(return_value=({"flow_name": "test"}, None))
    mock_flow_manager.handle_intent_change = Mock(return_value=None)
    mock_flow_manager.get_active_context.return_value = {
        "flow_id": "test_flow",
        "flow_name": "test",
    }

    mock_slot_extractor = Mock()
    mock_slot_extractor.acall = AsyncMock(return_value=[])

    # Setup Config with Patterns
    settings = SettingsConfig(
        patterns=PatternBehaviorsConfig(
            correction=CorrectionPatternConfig(response_template="Fixed {slot} to {new_value}."),
            clarification=ClarificationPatternConfig(response_template="It means {explanation}"),
            cancellation=CancellationPatternConfig(response_message="Cancelled!"),
            human_handoff=HumanHandoffPatternConfig(message="Calling human..."),
        )
    )

    config = SoniConfig(
        settings=settings,
        slots={
            "cvv": SlotConfig(type="string", description="The 3 digits on back"),
        },
    )

    ctx = RuntimeContext(
        config=config,
        flow_manager=mock_flow_manager,
        du=mock_du,
        slot_extractor=mock_slot_extractor,
        action_handler=Mock(),  # Partial mock
    )

    return ctx


@pytest.fixture
def run_config(mock_runtime_context):
    return RunnableConfig(configurable={"runtime_context": mock_runtime_context})


@pytest.mark.asyncio
async def test_understand_node_handles_correction(mock_runtime_context, run_config):
    """Test CorrectSlot command updates slot and adds response."""
    state: DialogueState = {
        "messages": [],
        "commands": [],
        "flow_slots": {},
        "user_message": "",
        "last_response": "",
        "flow_stack": [],
        "flow_state": FlowState.ACTIVE,
        "waiting_for_slot": None,
        "waiting_for_slot_type": None,
        "response": None,
        "action_result": None,
        "_branch_target": None,
        "turn_count": 0,
        "metadata": {},
    }

    # Mock NLU output
    initial_cmd = CorrectSlot(slot="name", new_value="Jim")
    mock_runtime_context.du.acall.return_value = NLUOutput(commands=[initial_cmd], confidence=1.0)

    result = await understand_node(state, run_config)

    # Verify slot update
    mock_runtime_context.flow_manager.set_slot.assert_called_with(state, "name", "Jim")

    # Verify response message
    assert "messages" in result
    msg = result["messages"][0].content
    assert "Fixed name to Jim" in msg
    assert result["last_response"] == "Fixed name to Jim."


@pytest.mark.asyncio
async def test_understand_node_handles_cancellation(mock_runtime_context, run_config):
    """Test CancelFlow command pops flow and adds response."""
    state: DialogueState = {
        "messages": [],
        "commands": [],
        "flow_slots": {},
        "flow_stack": [],
        "user_message": "",
        "last_response": "",
        "flow_state": FlowState.ACTIVE,
        "waiting_for_slot": None,
        "waiting_for_slot_type": None,
        "response": None,
        "action_result": None,
        "_branch_target": None,
        "turn_count": 0,
        "metadata": {},
    }

    mock_runtime_context.du.acall.return_value = NLUOutput(commands=[CancelFlow()], confidence=1.0)

    result = await understand_node(state, run_config)

    # Verify flow pop
    mock_runtime_context.flow_manager.pop_flow.assert_called_once()

    # Verify response
    msg = result["messages"][0].content
    assert "Cancelled!" in msg


@pytest.mark.asyncio
async def test_understand_node_handles_clarification(mock_runtime_context, run_config):
    """Test RequestClarification looks up description and responds."""
    state: DialogueState = {
        "messages": [],
        "commands": [],
        "flow_slots": {},
        "waiting_for_slot": "cvv",
        "user_message": "",
        "last_response": "",
        "flow_stack": [],
        "flow_state": FlowState.ACTIVE,
        "waiting_for_slot_type": None,
        "response": None,
        "action_result": None,
        "_branch_target": None,
        "turn_count": 0,
        "metadata": {},
    }

    # Request clarification for "cvv" (implicit via topic=None or explicit)
    cmd = RequestClarification(topic="cvv")
    mock_runtime_context.du.acall.return_value = NLUOutput(commands=[cmd], confidence=1.0)

    result = await understand_node(state, run_config)

    # Verify response uses description
    msg = result["messages"][0].content
    assert "It means The 3 digits on back" in msg


@pytest.mark.asyncio
async def test_understand_node_handles_handoff(mock_runtime_context, run_config):
    """Test HumanHandoff adds configured message."""
    state: DialogueState = {
        "messages": [],
        "commands": [],
        "flow_slots": {},
        "user_message": "",
        "last_response": "",
        "flow_stack": [],
        "flow_state": FlowState.ACTIVE,
        "waiting_for_slot": None,
        "waiting_for_slot_type": None,
        "response": None,
        "action_result": None,
        "_branch_target": None,
        "turn_count": 0,
        "metadata": {},
    }

    mock_runtime_context.du.acall.return_value = NLUOutput(
        commands=[HumanHandoff()], confidence=1.0
    )

    result = await understand_node(state, run_config)

    msg = result["messages"][0].content
    assert "Calling human..." in msg
