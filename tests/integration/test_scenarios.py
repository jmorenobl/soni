from unittest.mock import AsyncMock, Mock

import pytest
from langchain_core.messages import HumanMessage

from soni.actions.handler import ActionHandler
from soni.actions.registry import ActionRegistry
from soni.config import FlowConfig, SoniConfig
from soni.config.steps import CollectStepConfig, ConfirmStepConfig, SayStepConfig
from soni.core.commands import SetSlot, StartFlow
from soni.core.state import create_empty_dialogue_state
from soni.core.types import RuntimeContext
from soni.dm.builder import build_orchestrator
from soni.flow.manager import FlowManager


@pytest.fixture
def scenario_config():
    """Config with multiple flows for scenario testing."""
    return SoniConfig(
        flows={
            "book_flight": FlowConfig(
                description="Book a flight",
                steps=[
                    CollectStepConfig(step="ask_dest", slot="destination", message="Where to?"),
                    CollectStepConfig(step="ask_date", slot="date", message="When?"),
                    ConfirmStepConfig(step="confirm", slot="confirmed", message="Confirm booking?"),
                    SayStepConfig(step="done", message="Booked flight to {destination} on {date}"),
                ],
            ),
            "check_weather": FlowConfig(
                description="Check weather",
                steps=[
                    CollectStepConfig(step="ask_city", slot="city", message="Which city?"),
                    SayStepConfig(step="show_weather", message="Sunny in {city}"),
                ],
            ),
        }
    )


@pytest.mark.asyncio
async def test_scenario_interruption_and_resume(scenario_config):
    """
    Scenario:
    1. User starts 'book_flight' -> Collecting destination
    2. User says "what's the weather in London?" (INTERRUPTION)
    3. System handles weather flow, then resumes booking
    4. User provides "Paris" for destination

    With interrupt() API: verify flow stack changes and slot values
    """
    # Setup
    fm = FlowManager()
    registry = ActionRegistry()
    registry.clear()

    handler = ActionHandler(registry)

    # Mock NLU
    mock_du = AsyncMock()
    mock_du.acall.side_effect = [
        # Turn 1: book flight
        type("NLUOutput", (), {"commands": [StartFlow(flow_name="book_flight")]}),
        # Turn 2: weather in London (interruption while collecting destination)
        type(
            "NLUOutput",
            (),
            {
                "commands": [
                    StartFlow(flow_name="check_weather"),
                    SetSlot(slot="city", value="London"),
                ]
            },
        ),
        # Turn 3: Paris (resume booking, provide destination)
        type("NLUOutput", (), {"commands": [SetSlot(slot="destination", value="Paris")]}),
    ]

    # Build graph
    graph = build_orchestrator(scenario_config)
    ctx = RuntimeContext(
        config=scenario_config, flow_manager=fm, action_handler=handler, du=mock_du
    )
    run_config = {"configurable": {"thread_id": "test_scenario_1"}}

    # Turn 1: Start booking
    state = create_empty_dialogue_state()
    state["user_message"] = "book a flight"
    state["messages"] = [HumanMessage(content="book a flight")]

    result = await graph.ainvoke(state, config=run_config, context=ctx)

    # Verify: booking flow started
    assert len(result["flow_stack"]) == 1
    assert result["flow_stack"][0]["flow_name"] == "book_flight"

    # Turn 2: Weather interruption + intent change
    state = result
    state["user_message"] = "what's the weather in London?"
    state["messages"].append(HumanMessage(content="what's the weather in London?"))

    result = await graph.ainvoke(state, config=run_config, context=ctx)

    # Verify: weather flow on top, London slot set
    assert len(result["flow_stack"]) == 2
    assert result["flow_stack"][1]["flow_name"] == "check_weather"
    weather_flow_id = result["flow_stack"][1]["flow_id"]
    assert result["flow_slots"][weather_flow_id].get("city") == "London"
    # Should have weather message
    assert any("Sunny" in str(m.content) for m in result["messages"])

    # Turn 3: Resume booking with "Paris"
    state = result
    state["user_message"] = "Paris"
    state["messages"].append(HumanMessage(content="Paris"))

    result = await graph.ainvoke(state, config=run_config, context=ctx)

    # Verify: back to booking flow (weather completed)
    assert len(result["flow_stack"]) == 1
    assert result["flow_stack"][0]["flow_name"] == "book_flight"
    booking_flow_id = result["flow_stack"][0]["flow_id"]
    assert result["flow_slots"][booking_flow_id]["destination"] == "Paris"


@pytest.mark.asyncio
async def test_scenario_denial_cancel(scenario_config):
    """
    Scenario:
    1. Book flight to Paris Tomorrow (all slots provided)
    2. System reaches confirmation step
    3. User says "hmm" (no clear affirm/deny) -> Should call interrupt()

    With interrupt() API: verify confirmation interruption behavior
    """
    # Setup
    fm = FlowManager()
    registry = ActionRegistry()
    registry.clear()

    handler = ActionHandler(registry)

    # Mock NLU
    mock_du = AsyncMock()
    mock_du.acall.side_effect = [
        # Turn 1: book flight with all slots
        type(
            "NLUOutput",
            (),
            {
                "commands": [
                    StartFlow(flow_name="book_flight"),
                    SetSlot(slot="destination", value="Paris"),
                    SetSlot(slot="date", value="Tomorrow"),
                ]
            },
        ),
        # Turn 2: ambiguous response (no affirm/deny command)
        type("NLUOutput", (), {"commands": []}),
    ]

    # Build graph
    graph = build_orchestrator(scenario_config)
    ctx = RuntimeContext(
        config=scenario_config, flow_manager=fm, action_handler=handler, du=mock_du
    )
    run_config = {"configurable": {"thread_id": "test_scenario_2"}}

    # Turn 1: Book with all info
    state = create_empty_dialogue_state()
    state["user_message"] = "book flight to Paris tomorrow"
    state["messages"] = [HumanMessage(content="book flight to Paris tomorrow")]

    result = await graph.ainvoke(state, config=run_config, context=ctx)

    # Verify: flow started, slots collected
    assert len(result["flow_stack"]) == 1
    flow_id = result["flow_stack"][0]["flow_id"]
    assert result["flow_slots"][flow_id]["destination"] == "Paris"
    assert result["flow_slots"][flow_id]["date"] == "Tomorrow"

    # Turn 2: Ambiguous response -> should call interrupt() and return
    state = result
    state["user_message"] = "hmm"
    state["messages"].append(HumanMessage(content="hmm"))

    result = await graph.ainvoke(state, config=run_config, context=ctx)

    # With interrupt(): confirm node will interrupt and wait
    # The flow should still be active
    assert len(result["flow_stack"]) == 1
    # Confirmed slot should not be set yet (still waiting for clear answer)
    assert result["flow_slots"][flow_id].get("confirmed") is None
