"""Integration tests for dialogue manager with mocked NLU.

These tests verify that the dialogue manager works correctly regardless of NLU accuracy.
The NLU is completely mocked to isolate dialogue management logic from NLU performance.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from langgraph.checkpoint.memory import InMemorySaver

from soni.core.config import FlowConfig, SlotConfig, StepConfig, TriggerConfig
from soni.core.state import create_initial_state, get_all_slots
from soni.dm.builder import build_graph
from soni.du.models import MessageType, NLUOutput, SlotValue


@pytest.fixture
def flight_booking_config():
    """Create flight booking configuration for testing."""
    return {
        "version": "1.0.0",
        "settings": {
            "models": {
                "nlu": {
                    "provider": "openai",
                    "model": "gpt-4o-mini",
                },
            },
        },
        "flows": {
            "book_flight": {
                "description": "Book a flight",
                "trigger": {"intents": ["book_flight"]},
                "steps": [
                    {"step": "collect_origin", "type": "collect", "slot": "origin"},
                    {"step": "collect_destination", "type": "collect", "slot": "destination"},
                    {"step": "collect_date", "type": "collect", "slot": "departure_date"},
                    {"step": "confirm_booking", "type": "confirm"},
                    {"step": "search_flights", "type": "action", "action": "search_flights"},
                ],
            },
        },
        "slots": {
            "origin": {
                "type": "city",
                "prompt": "Which city are you departing from?",
            },
            "destination": {
                "type": "city",
                "prompt": "Where would you like to go?",
            },
            "departure_date": {
                "type": "date",
                "prompt": "When would you like to depart?",
            },
        },
        "actions": {
            "search_flights": {
                "handler": "soni.actions.registry:ActionRegistry",
            },
        },
    }


@pytest.fixture
def mock_nlu_provider():
    """Create a mock NLU provider that can be configured per test."""
    nlu = AsyncMock()
    return nlu


@pytest.fixture
def mock_action_handler():
    """Create a mock action handler."""
    handler = AsyncMock()
    handler.execute.return_value = {
        "booking_ref": "BK-123",
        "message": "Flight booked successfully",
    }
    return handler


@pytest.fixture
async def graph_with_mocked_nlu(flight_booking_config, mock_nlu_provider, mock_action_handler):
    """Build graph with mocked NLU provider."""
    from soni.core.config import SoniConfig
    from soni.core.scope import ScopeManager
    from soni.du.normalizer import SlotNormalizer
    from soni.flow.manager import FlowManager

    config = SoniConfig.from_dict(flight_booking_config)
    flow_manager = FlowManager()
    scope_manager = ScopeManager(config=config)
    normalizer = SlotNormalizer(config=config)

    context = {
        "flow_manager": flow_manager,
        "du": mock_nlu_provider,  # Use "du" key as expected by nodes
        "nlu_provider": mock_nlu_provider,  # Also provide for compatibility
        "action_handler": mock_action_handler,
        "scope_manager": scope_manager,
        "normalizer": normalizer,
        "config": config,
        "step_manager": MagicMock(),  # Will be set up per test
    }

    # Build graph with in-memory checkpointer
    graph = build_graph(context, checkpointer=InMemorySaver())
    return graph, mock_nlu_provider, context


@pytest.mark.integration
@pytest.mark.asyncio
async def test_digression_flow_with_mocked_nlu(graph_with_mocked_nlu):
    """
    Test complete digression flow with mocked NLU.

    Scenario:
    1. User triggers booking
    2. User provides origin
    3. User asks a question (digression) - NLU correctly classifies as clarification
    4. System responds and re-prompts for destination
    5. User provides destination
    6. System shows prompt for departure_date (not digression message)
    """
    graph, mock_nlu, context = graph_with_mocked_nlu
    user_id = "test-digression-1"
    config_dict = {"configurable": {"thread_id": user_id}}

    # Configure step_manager
    from soni.flow.step_manager import FlowStepManager

    step_manager = FlowStepManager(context["config"])
    context["step_manager"] = step_manager

    # Turn 1: User triggers booking
    mock_nlu.predict.return_value = NLUOutput(
        message_type=MessageType.SLOT_VALUE,
        command="book_flight",
        slots=[],
        confidence=0.95,
    )

    state1 = create_initial_state("I want to book a flight")
    result1 = await graph.ainvoke(state1, config=config_dict)

    # Verify flow started
    assert result1.get("flow_stack")
    assert result1.get("conversation_state") == "waiting_for_slot"
    assert result1.get("waiting_for_slot") == "origin"
    # When collect_next_slot interrupts, the prompt is in __interrupt__
    interrupt_value = result1.get("__interrupt__")
    if interrupt_value:
        # Extract prompt from interrupt
        prompt = (
            interrupt_value[0].value if isinstance(interrupt_value, list) else interrupt_value.value
        )
        assert "origin" in prompt.lower() or "depart" in prompt.lower()
    else:
        # If no interrupt, check last_response
        assert (
            "origin" in result1.get("last_response", "").lower()
            or "depart" in result1.get("last_response", "").lower()
        )

    # Turn 2: User provides origin
    mock_nlu.predict.return_value = NLUOutput(
        message_type=MessageType.SLOT_VALUE,
        command=None,
        slots=[SlotValue(name="origin", value="San Francisco", confidence=0.95)],
        confidence=0.95,
    )

    state2 = create_initial_state("San Francisco")
    state2.update(result1)  # Merge previous state
    result2 = await graph.ainvoke(state2, config=config_dict)

    # Verify origin was saved and advanced to destination
    slots = get_all_slots(result2)
    assert slots.get("origin") == "San Francisco"
    assert result2.get("waiting_for_slot") == "destination"
    # Check interrupt or last_response
    interrupt_value = result2.get("__interrupt__")
    if interrupt_value:
        prompt = (
            interrupt_value[0].value if isinstance(interrupt_value, list) else interrupt_value.value
        )
        assert "destination" in prompt.lower() or "go" in prompt.lower()
    else:
        assert (
            "destination" in result2.get("last_response", "").lower()
            or "go" in result2.get("last_response", "").lower()
        )

    # Turn 3: User asks a question (digression) - NLU correctly classifies
    mock_nlu.predict.return_value = NLUOutput(
        message_type=MessageType.CLARIFICATION,
        command=None,
        slots=[],
        confidence=0.9,
    )

    state3 = create_initial_state("What airports do you support?")
    state3.update(result2)  # Merge previous state
    result3 = await graph.ainvoke(state3, config=config_dict)

    # Verify digression was handled correctly
    assert result3.get("waiting_for_slot") == "destination"  # Preserved
    assert result3.get("conversation_state") == "waiting_for_slot"
    # Should include both digression response and re-prompt
    last_response = result3.get("last_response", "")
    assert "destination" in last_response.lower() or "go" in last_response.lower()
    # Should mention question/help
    assert (
        "question" in last_response.lower()
        or "help" in last_response.lower()
        or "understand" in last_response.lower()
    )

    # Turn 4: User provides destination
    mock_nlu.predict.return_value = NLUOutput(
        message_type=MessageType.SLOT_VALUE,
        command=None,
        slots=[SlotValue(name="destination", value="Miami", confidence=0.95)],
        confidence=0.95,
    )

    state4 = create_initial_state("Miami")
    state4.update(result3)  # Merge previous state
    result4 = await graph.ainvoke(state4, config=config_dict)

    # Verify destination was saved and advanced to departure_date
    slots = get_all_slots(result4)
    assert slots.get("destination") == "Miami"
    assert result4.get("waiting_for_slot") == "departure_date"
    # CRITICAL: Should show prompt for departure_date, NOT digression message
    interrupt_value = result4.get("__interrupt__")
    if interrupt_value:
        prompt = (
            interrupt_value[0].value if isinstance(interrupt_value, list) else interrupt_value.value
        )
        assert (
            "departure_date" in prompt.lower()
            or "depart" in prompt.lower()
            or "when" in prompt.lower()
        )
        # Should NOT contain digression message
        assert "airports" not in prompt.lower()
        assert "question" not in prompt.lower() or "when" in prompt.lower()
    else:
        last_response = result4.get("last_response", "")
        assert (
            "departure_date" in last_response.lower()
            or "depart" in last_response.lower()
            or "when" in last_response.lower()
        )
        # Should NOT contain digression message
        assert "airports" not in last_response.lower()
        assert "question" not in last_response.lower() or "when" in last_response.lower()


@pytest.mark.integration
@pytest.mark.asyncio
async def test_digression_flow_nlu_misclassifies_as_slot_value(graph_with_mocked_nlu):
    """
    Test digression flow when NLU misclassifies question as slot_value.

    This tests the robustness of the dialogue manager when NLU makes mistakes.
    The system should handle this gracefully without breaking the flow.
    """
    graph, mock_nlu, context = graph_with_mocked_nlu
    user_id = "test-digression-2"
    config_dict = {"configurable": {"thread_id": user_id}}

    # Configure step_manager
    from soni.flow.step_manager import FlowStepManager

    step_manager = FlowStepManager(context["config"])
    context["step_manager"] = step_manager

    # Turn 1: User triggers booking
    mock_nlu.predict.return_value = NLUOutput(
        message_type=MessageType.SLOT_VALUE,
        command="book_flight",
        slots=[],
        confidence=0.95,
    )

    state1 = create_initial_state("I want to book a flight")
    result1 = await graph.ainvoke(state1, config=config_dict)

    # Turn 2: User provides origin
    mock_nlu.predict.return_value = NLUOutput(
        message_type=MessageType.SLOT_VALUE,
        command=None,
        slots=[SlotValue(name="origin", value="San Francisco", confidence=0.95)],
        confidence=0.95,
    )

    state2 = create_initial_state("San Francisco")
    state2.update(result1)
    result2 = await graph.ainvoke(state2, config=config_dict)

    # Turn 3: User asks question, but NLU MISCLASSIFIES as slot_value
    # This simulates the real-world scenario where NLU makes mistakes
    mock_nlu.predict.return_value = NLUOutput(
        message_type=MessageType.SLOT_VALUE,  # WRONG - should be clarification/digression
        command=None,
        slots=[],  # No slots extracted (correctly)
        confidence=0.5,  # Low confidence
    )

    state3 = create_initial_state("What airports do you support?")
    state3.update(result2)
    result3 = await graph.ainvoke(state3, config=config_dict)

    # System should handle this gracefully
    # It should either:
    # 1. Detect no slots and re-prompt for destination, OR
    # 2. Handle it as an error and re-prompt
    # The important thing is that the flow doesn't break
    assert result3.get("waiting_for_slot") == "destination"  # Should preserve
    # Should re-prompt for destination (even if message is generic)
    last_response = result3.get("last_response", "")
    assert len(last_response) > 0  # Should have some response
    # Flow should still be active
    assert result3.get("flow_stack")


@pytest.mark.integration
@pytest.mark.asyncio
async def test_slot_correction_flow_with_mocked_nlu(graph_with_mocked_nlu):
    """
    Test slot correction flow with mocked NLU.

    Scenario:
    1. User provides origin
    2. User provides destination
    3. User corrects origin
    4. System acknowledges and re-prompts for next slot
    """
    graph, mock_nlu, context = graph_with_mocked_nlu
    user_id = "test-correction-1"
    config_dict = {"configurable": {"thread_id": user_id}}

    # Configure step_manager
    from soni.flow.step_manager import FlowStepManager

    step_manager = FlowStepManager(context["config"])
    context["step_manager"] = step_manager

    # Turn 1: User triggers booking
    mock_nlu.predict.return_value = NLUOutput(
        message_type=MessageType.SLOT_VALUE,
        command="book_flight",
        slots=[],
        confidence=0.95,
    )

    state1 = create_initial_state("I want to book a flight")
    result1 = await graph.ainvoke(state1, config=config_dict)

    # Turn 2: User provides origin
    mock_nlu.predict.return_value = NLUOutput(
        message_type=MessageType.SLOT_VALUE,
        command=None,
        slots=[SlotValue(name="origin", value="Chicago", confidence=0.95)],
        confidence=0.95,
    )

    state2 = create_initial_state("Chicago")
    state2.update(result1)
    result2 = await graph.ainvoke(state2, config=config_dict)

    # Turn 3: User provides destination
    mock_nlu.predict.return_value = NLUOutput(
        message_type=MessageType.SLOT_VALUE,
        command=None,
        slots=[SlotValue(name="destination", value="Miami", confidence=0.95)],
        confidence=0.95,
    )

    state3 = create_initial_state("Miami")
    state3.update(result2)
    result3 = await graph.ainvoke(state3, config=config_dict)

    # Turn 4: User corrects origin
    mock_nlu.predict.return_value = NLUOutput(
        message_type=MessageType.CORRECTION,
        command=None,
        slots=[SlotValue(name="origin", value="Denver", confidence=0.95, action="correct")],
        confidence=0.95,
    )

    state4 = create_initial_state("Actually, I meant Denver")
    state4.update(result3)
    result4 = await graph.ainvoke(state4, config=config_dict)

    # Verify correction was handled
    slots = get_all_slots(result4)
    assert slots.get("origin") == "Denver"  # Updated
    assert slots.get("destination") == "Miami"  # Preserved
    # Should re-prompt for next slot (departure_date)
    assert result4.get("waiting_for_slot") == "departure_date"
    last_response = result4.get("last_response", "")
    # Should acknowledge correction
    assert (
        "denver" in last_response.lower()
        or "updated" in last_response.lower()
        or "changed" in last_response.lower()
    )
    # Should re-prompt for departure_date
    assert (
        "departure_date" in last_response.lower()
        or "depart" in last_response.lower()
        or "when" in last_response.lower()
    )
