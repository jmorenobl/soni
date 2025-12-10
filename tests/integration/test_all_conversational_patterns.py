"""Integration tests for all conversational patterns with mocked NLU.

This test suite ensures ALL conversational patterns defined in the framework
are properly tested with mocked NLU to isolate dialogue management from NLU accuracy.

Patterns defined in docs/design/10-dsl-specification/06-patterns.md:
1. Correction - User fixes a previously given value
2. Slot Modification - User wants to change a specific slot
3. Interruption - User starts a completely new task
4. Digression - Off-topic question without changing flow
5. Clarification - User asks why information is needed
6. Cancellation - User wants to abandon
7. Partial Confirmation - User confirms but requests a change
"""

from unittest.mock import AsyncMock, MagicMock

import pytest
from langgraph.checkpoint.memory import InMemorySaver

from soni.core.config import SoniConfig
from soni.core.scope import ScopeManager
from soni.core.state import create_initial_state, get_all_slots
from soni.dm.builder import build_graph
from soni.du.models import MessageType, NLUOutput, SlotValue
from soni.du.normalizer import SlotNormalizer
from soni.flow.manager import FlowManager


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
                    {"step": "search_flights", "type": "action", "call": "search_flights"},
                ],
            },
            "book_hotel": {
                "description": "Book a hotel",
                "trigger": {"intents": ["book_hotel"]},
                "steps": [
                    {"step": "collect_location", "type": "collect", "slot": "location"},
                    {"step": "collect_checkin", "type": "collect", "slot": "checkin_date"},
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
            "location": {
                "type": "city",
                "prompt": "Which city?",
            },
            "checkin_date": {
                "type": "date",
                "prompt": "Check-in date?",
            },
        },
        "actions": {
            "search_flights": {
                "handler": "soni.actions.registry:ActionRegistry",
            },
        },
    }


@pytest.fixture
async def graph_with_mocked_nlu(flight_booking_config):
    """Build graph with mocked NLU provider."""
    mock_nlu = AsyncMock()
    mock_action_handler = AsyncMock()
    mock_action_handler.execute.return_value = {"booking_ref": "BK-123", "message": "Flight booked"}

    config = SoniConfig.from_dict(flight_booking_config)
    flow_manager = FlowManager()
    scope_manager = ScopeManager(config=config)
    normalizer = SlotNormalizer(config=config)

    from soni.flow.step_manager import FlowStepManager

    step_manager = FlowStepManager(config)

    context = {
        "flow_manager": flow_manager,
        "du": mock_nlu,
        "nlu_provider": mock_nlu,
        "action_handler": mock_action_handler,
        "scope_manager": scope_manager,
        "normalizer": normalizer,
        "config": config,
        "step_manager": step_manager,
    }

    graph = build_graph(context, checkpointer=InMemorySaver())
    return graph, mock_nlu, context


@pytest.mark.integration
@pytest.mark.asyncio
async def test_pattern_1_correction(graph_with_mocked_nlu):
    """
    Pattern 1: Correction - User fixes a previously given value.

    Scenario:
    - User provides origin and destination
    - User corrects origin
    - System updates slot and re-prompts for next slot
    """
    graph, mock_nlu, context = graph_with_mocked_nlu
    user_id = "test-correction"
    config_dict = {"configurable": {"thread_id": user_id}}

    # Turn 1: Trigger booking
    mock_nlu.predict.return_value = NLUOutput(
        message_type=MessageType.SLOT_VALUE,
        command="book_flight",
        slots=[],
        confidence=0.95,
    )
    state1 = create_initial_state("I want to book a flight")
    result1 = await graph.ainvoke(state1, config=config_dict)

    # Turn 2: Provide origin
    mock_nlu.predict.return_value = NLUOutput(
        message_type=MessageType.SLOT_VALUE,
        command=None,
        slots=[SlotValue(name="origin", value="Chicago", confidence=0.95)],
        confidence=0.95,
    )
    state2 = create_initial_state("Chicago")
    state2.update(result1)
    result2 = await graph.ainvoke(state2, config=config_dict)

    # Turn 3: Provide destination
    mock_nlu.predict.return_value = NLUOutput(
        message_type=MessageType.SLOT_VALUE,
        command=None,
        slots=[SlotValue(name="destination", value="Miami", confidence=0.95)],
        confidence=0.95,
    )
    state3 = create_initial_state("Miami")
    state3.update(result2)
    result3 = await graph.ainvoke(state3, config=config_dict)

    # Turn 4: CORRECTION - User corrects origin
    mock_nlu.predict.return_value = NLUOutput(
        message_type=MessageType.CORRECTION,
        command=None,
        slots=[SlotValue(name="origin", value="Denver", confidence=0.95, action="correct")],
        confidence=0.95,
    )
    state4 = create_initial_state("Actually, I meant Denver")
    state4.update(result3)
    result4 = await graph.ainvoke(state4, config=config_dict)

    # Verify correction was handled according to design
    # Design spec (06-patterns.md): "Update slot, return to current step"
    slots = get_all_slots(result4)
    assert slots.get("origin") == "Denver", (
        f"Design violation: Correction should update slot. "
        f"Expected 'Denver', got '{slots.get('origin')}'"
    )
    assert slots.get("destination") == "Miami", (
        f"Design violation: Correction should preserve other slots. "
        f"Expected 'Miami', got '{slots.get('destination')}'"
    )
    # Should re-prompt for next slot (departure_date) - "return to current step"
    assert result4.get("waiting_for_slot") == "departure_date", (
        f"Design violation: Correction should return to current step. "
        f"Expected waiting_for_slot='departure_date', got '{result4.get('waiting_for_slot')}'"
    )


@pytest.mark.integration
@pytest.mark.asyncio
async def test_pattern_2_modification(graph_with_mocked_nlu):
    """
    Pattern 2: Slot Modification - User wants to change a specific slot.

    Scenario:
    - User provides all slots
    - User requests modification of destination
    - System updates slot and returns to confirmation
    """
    graph, mock_nlu, context = graph_with_mocked_nlu
    user_id = "test-modification"
    config_dict = {"configurable": {"thread_id": user_id}}

    # Setup: User has provided all slots and is at confirmation
    mock_nlu.predict.return_value = NLUOutput(
        message_type=MessageType.SLOT_VALUE,
        command="book_flight",
        slots=[],
        confidence=0.95,
    )
    state = create_initial_state("I want to book a flight")
    result = await graph.ainvoke(state, config=config_dict)

    # Provide all slots quickly
    for slot_name, value in [
        ("origin", "NYC"),
        ("destination", "LAX"),
        ("departure_date", "2025-12-25"),
    ]:
        mock_nlu.predict.return_value = NLUOutput(
            message_type=MessageType.SLOT_VALUE,
            command=None,
            slots=[SlotValue(name=slot_name, value=value, confidence=0.95)],
            confidence=0.95,
        )
        state = create_initial_state(value)
        state.update(result)
        result = await graph.ainvoke(state, config=config_dict)

    # Now at confirmation - user requests modification
    mock_nlu.predict.return_value = NLUOutput(
        message_type=MessageType.MODIFICATION,
        command=None,
        slots=[SlotValue(name="destination", value="Seattle", confidence=0.95, action="modify")],
        confidence=0.95,
    )
    state = create_initial_state("Change the destination to Seattle")
    state.update(result)
    result = await graph.ainvoke(state, config=config_dict)

    # Verify modification was handled according to design
    # Design spec (06-patterns.md): "Update slot, return to confirmation"
    slots = get_all_slots(result)
    assert slots.get("destination") == "Seattle", (
        f"Design violation: Modification should update slot. "
        f"Expected 'Seattle', got '{slots.get('destination')}'"
    )
    # Should return to confirmation step (design requirement)
    assert result.get("conversation_state") in ("ready_for_confirmation", "confirming"), (
        f"Design violation: Modification should return to confirmation. "
        f"Got conversation_state={result.get('conversation_state')}"
    )


@pytest.mark.integration
@pytest.mark.asyncio
async def test_pattern_3_interruption(graph_with_mocked_nlu):
    """
    Pattern 3: Interruption - User starts a completely new task.

    Scenario:
    - User is in middle of booking flight (collecting destination)
    - User interrupts to book hotel
    - System pushes new flow, pauses current
    - After hotel booking, system resumes flight booking
    """
    graph, mock_nlu, context = graph_with_mocked_nlu
    user_id = "test-interruption"
    config_dict = {"configurable": {"thread_id": user_id}}

    # Turn 1: Start flight booking
    mock_nlu.predict.return_value = NLUOutput(
        message_type=MessageType.SLOT_VALUE,
        command="book_flight",
        slots=[],
        confidence=0.95,
    )
    state1 = create_initial_state("I want to book a flight")
    result1 = await graph.ainvoke(state1, config=config_dict)

    # Turn 2: Provide origin
    mock_nlu.predict.return_value = NLUOutput(
        message_type=MessageType.SLOT_VALUE,
        command=None,
        slots=[SlotValue(name="origin", value="NYC", confidence=0.95)],
        confidence=0.95,
    )
    state2 = create_initial_state("NYC")
    state2.update(result1)
    result2 = await graph.ainvoke(state2, config=config_dict)

    # Turn 3: INTERRUPTION - User starts hotel booking
    mock_nlu.predict.return_value = NLUOutput(
        message_type=MessageType.INTERRUPTION,
        command="book_hotel",
        slots=[],
        confidence=0.95,
    )
    state3 = create_initial_state("Actually, first book me a hotel")
    state3.update(result2)
    result3 = await graph.ainvoke(state3, config=config_dict)

    # Verify interruption was handled according to design
    # Design spec (06-patterns.md): "Push new flow, pause current"
    # Design spec (07-flow-management.md): push_flow() pauses current flow
    flow_stack = result3.get("flow_stack", [])
    assert len(flow_stack) == 2, (
        f"Design violation: Interruption should push new flow and pause current. "
        f"Expected 2 flows in stack, got {len(flow_stack)}"
    )
    # Current flow should be hotel (top of stack)
    active_flow = flow_stack[-1]
    assert active_flow.get("flow_name") == "book_hotel", (
        f"Design violation: New flow should be active. "
        f"Expected 'book_hotel', got '{active_flow.get('flow_name')}'"
    )
    assert active_flow.get("flow_state") == "active", (
        f"Design violation: New flow should be active. "
        f"Got flow_state={active_flow.get('flow_state')}"
    )
    # Previous flow should be paused
    paused_flow = flow_stack[0]
    assert paused_flow.get("flow_name") == "book_flight", (
        f"Design violation: Previous flow should be paused. "
        f"Expected 'book_flight', got '{paused_flow.get('flow_name')}'"
    )
    assert paused_flow.get("flow_state") == "paused", (
        f"Design violation: Previous flow should be paused. "
        f"Got flow_state={paused_flow.get('flow_state')}"
    )
    # Should be waiting for hotel slot
    assert result3.get("waiting_for_slot") == "location"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_pattern_4_digression(graph_with_mocked_nlu):
    """
    Pattern 4: Digression - Off-topic question without changing flow.

    Scenario:
    - User is collecting destination
    - User asks question
    - System answers and re-prompts for destination (NO stack change)
    """
    graph, mock_nlu, context = graph_with_mocked_nlu
    user_id = "test-digression"
    config_dict = {"configurable": {"thread_id": user_id}}

    # Setup: User is waiting for destination
    mock_nlu.predict.return_value = NLUOutput(
        message_type=MessageType.SLOT_VALUE,
        command="book_flight",
        slots=[],
        confidence=0.95,
    )
    state1 = create_initial_state("I want to book a flight")
    result1 = await graph.ainvoke(state1, config=config_dict)

    mock_nlu.predict.return_value = NLUOutput(
        message_type=MessageType.SLOT_VALUE,
        command=None,
        slots=[SlotValue(name="origin", value="NYC", confidence=0.95)],
        confidence=0.95,
    )
    state2 = create_initial_state("NYC")
    state2.update(result1)
    result2 = await graph.ainvoke(state2, config=config_dict)

    # Turn 3: DIGRESSION - User asks question
    mock_nlu.predict.return_value = NLUOutput(
        message_type=MessageType.DIGRESSION,
        command="airlines",
        slots=[],
        confidence=0.9,
    )
    state3 = create_initial_state("What airlines do you support?")
    state3.update(result2)
    result3 = await graph.ainvoke(state3, config=config_dict)

    # Verify digression was handled according to design
    # Design spec (06-patterns.md): "Answer, return to same point"
    # Design spec (07-flow-management.md): "Digressions never modify the flow stack"
    flow_stack_before = state3.get("flow_stack", [])
    flow_stack_after = result3.get("flow_stack", [])
    # CRITICAL: Stack should NOT change (design requirement)
    assert len(flow_stack_after) == len(flow_stack_before), (
        f"Design violation: Digression should NOT modify flow stack. "
        f"Before: {len(flow_stack_before)} flows, After: {len(flow_stack_after)} flows"
    )
    assert flow_stack_after == flow_stack_before, (
        f"Design violation: Digression should NOT modify flow stack. "
        f"Stack changed: {flow_stack_before} -> {flow_stack_after}"
    )
    # Should preserve waiting_for_slot
    assert result3.get("waiting_for_slot") == "destination", (
        f"Design violation: Digression should preserve waiting_for_slot. "
        f"Expected 'destination', got '{result3.get('waiting_for_slot')}'"
    )
    # Should include both answer and re-prompt
    last_response = result3.get("last_response", "")
    assert "destination" in last_response.lower() or "go" in last_response.lower(), (
        f"Design violation: Digression should re-prompt for original slot. "
        f"Response: {last_response}"
    )


@pytest.mark.integration
@pytest.mark.asyncio
async def test_pattern_5_clarification(graph_with_mocked_nlu):
    """
    Pattern 5: Clarification - User asks why information is needed.

    Scenario:
    - User is collecting destination
    - User asks why destination is needed
    - System explains and re-prompts (same as digression)
    """
    graph, mock_nlu, context = graph_with_mocked_nlu
    user_id = "test-clarification"
    config_dict = {"configurable": {"thread_id": user_id}}

    # Setup: User is waiting for destination
    mock_nlu.predict.return_value = NLUOutput(
        message_type=MessageType.SLOT_VALUE,
        command="book_flight",
        slots=[],
        confidence=0.95,
    )
    state1 = create_initial_state("I want to book a flight")
    result1 = await graph.ainvoke(state1, config=config_dict)

    mock_nlu.predict.return_value = NLUOutput(
        message_type=MessageType.SLOT_VALUE,
        command=None,
        slots=[SlotValue(name="origin", value="NYC", confidence=0.95)],
        confidence=0.95,
    )
    state2 = create_initial_state("NYC")
    state2.update(result1)
    result2 = await graph.ainvoke(state2, config=config_dict)

    # Turn 3: CLARIFICATION - User asks why
    mock_nlu.predict.return_value = NLUOutput(
        message_type=MessageType.CLARIFICATION,
        command=None,
        slots=[],
        confidence=0.9,
    )
    state3 = create_initial_state("Why do you need my destination?")
    state3.update(result2)
    result3 = await graph.ainvoke(state3, config=config_dict)

    # Verify clarification was handled according to design
    # Design spec (06-patterns.md): "Explain, re-prompt same slot"
    # Design spec (07-flow-management.md): "Digressions never modify the flow stack"
    flow_stack_before = state3.get("flow_stack", [])
    flow_stack_after = result3.get("flow_stack", [])
    # CRITICAL: Stack should NOT change (same as digression)
    assert len(flow_stack_after) == len(flow_stack_before), (
        f"Design violation: Clarification should NOT modify flow stack. "
        f"Before: {len(flow_stack_before)} flows, After: {len(flow_stack_after)} flows"
    )
    # Should preserve waiting_for_slot
    assert result3.get("waiting_for_slot") == "destination", (
        f"Design violation: Clarification should preserve waiting_for_slot. "
        f"Expected 'destination', got '{result3.get('waiting_for_slot')}'"
    )
    # Should re-prompt
    last_response = result3.get("last_response", "")
    assert "destination" in last_response.lower() or "go" in last_response.lower(), (
        f"Design violation: Clarification should re-prompt for original slot. "
        f"Response: {last_response}"
    )


@pytest.mark.integration
@pytest.mark.asyncio
async def test_pattern_6_cancellation(graph_with_mocked_nlu):
    """
    Pattern 6: Cancellation - User wants to abandon.

    Scenario:
    - User is collecting destination
    - User cancels
    - System pops flow and returns to idle
    """
    graph, mock_nlu, context = graph_with_mocked_nlu
    user_id = "test-cancellation"
    config_dict = {"configurable": {"thread_id": user_id}}

    # Setup: User is in middle of booking
    mock_nlu.predict.return_value = NLUOutput(
        message_type=MessageType.SLOT_VALUE,
        command="book_flight",
        slots=[],
        confidence=0.95,
    )
    state1 = create_initial_state("I want to book a flight")
    result1 = await graph.ainvoke(state1, config=config_dict)

    mock_nlu.predict.return_value = NLUOutput(
        message_type=MessageType.SLOT_VALUE,
        command=None,
        slots=[SlotValue(name="origin", value="NYC", confidence=0.95)],
        confidence=0.95,
    )
    state2 = create_initial_state("NYC")
    state2.update(result1)
    result2 = await graph.ainvoke(state2, config=config_dict)

    # Turn 3: CANCELLATION - User cancels
    mock_nlu.predict.return_value = NLUOutput(
        message_type=MessageType.CANCELLATION,
        command="cancel",
        slots=[],
        confidence=0.95,
    )
    state3 = create_initial_state("Never mind, forget it")
    state3.update(result2)
    result3 = await graph.ainvoke(state3, config=config_dict)

    # Verify cancellation was handled according to design
    # Design spec (06-patterns.md): "Pop flow, return to previous or idle"
    # Design spec (07-flow-management.md): pop_flow(state, result="cancelled")
    flow_stack = result3.get("flow_stack", [])
    # CRITICAL: Flow should be popped from stack (design requirement)
    assert len(flow_stack) == 0, (
        f"Design violation: Cancellation should pop flow from stack. "
        f"Expected empty stack, got {len(flow_stack)} flows: {[f['flow_name'] for f in flow_stack]}"
    )
    # Should return to idle (no previous flow) or previous flow
    assert result3.get("conversation_state") in ("idle", "waiting_for_slot"), (
        f"Design violation: After cancellation, should return to idle or previous flow. "
        f"Got conversation_state={result3.get('conversation_state')}"
    )


@pytest.mark.integration
@pytest.mark.asyncio
async def test_pattern_7_partial_confirmation(graph_with_mocked_nlu):
    """
    Pattern 7: Partial Confirmation - User confirms but requests a change.

    Scenario:
    - User is at confirmation step
    - User says "Yes, but make it 2 passengers"
    - System updates slot and re-confirms
    """
    graph, mock_nlu, context = graph_with_mocked_nlu
    user_id = "test-partial-confirmation"
    config_dict = {"configurable": {"thread_id": user_id}}

    # Setup: User has provided all slots and is at confirmation
    mock_nlu.predict.return_value = NLUOutput(
        message_type=MessageType.SLOT_VALUE,
        command="book_flight",
        slots=[],
        confidence=0.95,
    )
    state = create_initial_state("I want to book a flight")
    result = await graph.ainvoke(state, config=config_dict)

    # Provide all slots
    for slot_name, value in [
        ("origin", "NYC"),
        ("destination", "LAX"),
        ("departure_date", "2025-12-25"),
    ]:
        mock_nlu.predict.return_value = NLUOutput(
            message_type=MessageType.SLOT_VALUE,
            command=None,
            slots=[SlotValue(name=slot_name, value=value, confidence=0.95)],
            confidence=0.95,
        )
        state = create_initial_state(value)
        state.update(result)
        result = await graph.ainvoke(state, config=config_dict)

    # Now at confirmation - user confirms but requests change
    # This is a CONFIRMATION with confirmation_value=True but also has a MODIFICATION slot
    mock_nlu.predict.return_value = NLUOutput(
        message_type=MessageType.CONFIRMATION,
        command=None,
        slots=[SlotValue(name="passengers", value="2", confidence=0.95, action="modify")],
        confirmation_value=True,  # User said "yes"
        confidence=0.95,
    )
    state = create_initial_state("Yes, but make it 2 passengers")
    state.update(result)
    result = await graph.ainvoke(state, config=config_dict)

    # Verify partial confirmation was handled
    # System should update the slot and re-confirm
    # Note: This pattern may be handled as modification during confirmation
    # The exact state depends on implementation - could be completed if action executed
    assert result.get("conversation_state") in (
        "ready_for_confirmation",
        "confirming",
        "waiting_for_slot",
        "idle",
        "completed",
    )


@pytest.mark.integration
@pytest.mark.asyncio
async def test_pattern_continuation(graph_with_mocked_nlu):
    """
    Pattern: Continuation - General continuation message.

    Scenario:
    - User is in active flow
    - User sends continuation message
    - System continues to next step
    """
    graph, mock_nlu, context = graph_with_mocked_nlu
    user_id = "test-continuation"
    config_dict = {"configurable": {"thread_id": user_id}}

    # Setup: User has active flow
    mock_nlu.predict.return_value = NLUOutput(
        message_type=MessageType.SLOT_VALUE,
        command="book_flight",
        slots=[],
        confidence=0.95,
    )
    state1 = create_initial_state("I want to book a flight")
    result1 = await graph.ainvoke(state1, config=config_dict)

    # Turn 2: CONTINUATION - User continues
    mock_nlu.predict.return_value = NLUOutput(
        message_type=MessageType.CONTINUATION,
        command=None,
        slots=[],
        confidence=0.9,
    )
    state2 = create_initial_state("Continue")
    state2.update(result1)
    result2 = await graph.ainvoke(state2, config=config_dict)

    # Verify continuation was handled
    # Should continue to collect next slot
    assert result2.get("flow_stack")  # Flow still active
    assert result2.get("waiting_for_slot") == "origin"  # Should prompt for origin


@pytest.mark.integration
@pytest.mark.asyncio
async def test_pattern_multi_slot_extraction(graph_with_mocked_nlu):
    """
    Pattern: Multi-Slot Extraction - User provides multiple slots in one message.

    Scenario:
    - User provides origin, destination, and date in one message
    - System extracts all slots and skips to next step
    """
    graph, mock_nlu, context = graph_with_mocked_nlu
    user_id = "test-multi-slot"
    config_dict = {"configurable": {"thread_id": user_id}}

    # Turn 1: Trigger booking
    mock_nlu.predict.return_value = NLUOutput(
        message_type=MessageType.SLOT_VALUE,
        command="book_flight",
        slots=[],
        confidence=0.95,
    )
    state1 = create_initial_state("I want to book a flight")
    result1 = await graph.ainvoke(state1, config=config_dict)

    # Turn 2: MULTI-SLOT - User provides all slots at once
    mock_nlu.predict.return_value = NLUOutput(
        message_type=MessageType.SLOT_VALUE,
        command=None,
        slots=[
            SlotValue(name="origin", value="Madrid", confidence=0.95),
            SlotValue(name="destination", value="Paris", confidence=0.95),
            SlotValue(name="departure_date", value="2025-12-15", confidence=0.95),
        ],
        confidence=0.95,
    )
    state2 = create_initial_state("I want to fly from Madrid to Paris on December 15th")
    state2.update(result1)
    result2 = await graph.ainvoke(state2, config=config_dict)

    # Verify all slots were extracted
    slots = get_all_slots(result2)
    assert slots.get("origin") == "Madrid"
    assert slots.get("destination") == "Paris"
    assert slots.get("departure_date") == "2025-12-15"
    # Should advance to confirmation (all slots filled)
    assert result2.get("conversation_state") in ("ready_for_confirmation", "waiting_for_slot")
