from unittest.mock import AsyncMock

import pytest
from langchain_core.messages import HumanMessage
from soni.actions.handler import ActionHandler
from soni.actions.registry import ActionRegistry
from soni.core.commands import SetSlot, StartFlow
from soni.core.state import create_empty_dialogue_state
from soni.core.types import RuntimeContext
from soni.dm.builder import build_orchestrator
from soni.flow.manager import FlowManager

from soni.config import FlowConfig, SoniConfig
from soni.config.steps import CollectStepConfig, ConfirmStepConfig, SayStepConfig


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
    Scenario testing auto-resume behavior with interruption.

    Turn 1: Start book_flight
    Turn 2: Interrupt with check_weather WITHOUT providing city -> stack = 2
    Turn 3: Provide city for weather -> weather completes, auto-resume -> stack = 1
    Turn 4: Provide destination for booking

    This tests that flows auto-resume when completed.
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
        # Turn 2: weather WITHOUT city (interruption - will ask for city)
        type("NLUOutput", (), {"commands": [StartFlow(flow_name="check_weather")]}),
        # Turn 3: Provide London for weather -> completes and auto-resumes
        type("NLUOutput", (), {"commands": [SetSlot(slot="city", value="London")]}),
        # Turn 4: Paris for booking destination
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

    assert len(result["flow_stack"]) == 1
    assert result["flow_stack"][0]["flow_name"] == "book_flight"

    # Turn 2: Weather interruption WITHOUT city -> should push weather flow
    state = result
    state["user_message"] = "what's the weather"
    state["messages"].append(HumanMessage(content="what's the weather"))
    result = await graph.ainvoke(state, config=run_config, context=ctx)

    # NOW we should have 2 flows: book_flight + check_weather (waiting for city)
    assert len(result["flow_stack"]) == 2
    assert result["flow_stack"][0]["flow_name"] == "book_flight"
    assert result["flow_stack"][1]["flow_name"] == "check_weather"

    # Turn 3: Provide London -> weather completes and auto-resumes booking
    state = result
    state["user_message"] = "London"
    state["messages"].append(HumanMessage(content="London"))
    result = await graph.ainvoke(state, config=run_config, context=ctx)

    # Weather completed and popped - back to booking
    assert len(result["flow_stack"]) == 1
    assert result["flow_stack"][0]["flow_name"] == "book_flight"
    # Should have weather message
    assert any("Sunny" in str(m.content) for m in result["messages"])

    # Turn 4: Provide Paris for destination
    state = result
    state["user_message"] = "Paris"
    state["messages"].append(HumanMessage(content="Paris"))
    result = await graph.ainvoke(state, config=run_config, context=ctx)

    # Destination should be set
    booking_flow_id = result["flow_stack"][0]["flow_id"]
    assert result["flow_slots"][booking_flow_id]["destination"] == "Paris"


@pytest.mark.asyncio
async def test_scenario_denial_cancel(scenario_config):
    """
    Scenario testing confirmation with ambiguous response.

    Turn 1: Book flight with all slots -> reaches confirmation
    Turn 2: Ambiguous response "hmm" -> no affirm/deny -> interrupt() called

    This tests that confirmation calls interrupt() when no clear response.
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

    # Turn 1: Book with all info -> should reach confirmation step
    state = create_empty_dialogue_state()
    state["user_message"] = "book flight to Paris tomorrow"
    state["messages"] = [HumanMessage(content="book flight to Paris tomorrow")]
    result = await graph.ainvoke(state, config=run_config, context=ctx)

    # Verify: slots collected
    assert len(result["flow_stack"]) == 1
    flow_id = result["flow_stack"][0]["flow_id"]
    assert result["flow_slots"][flow_id]["destination"] == "Paris"
    assert result["flow_slots"][flow_id]["date"] == "Tomorrow"

    # Turn 2: Ambiguous response -> confirm node calls interrupt()
    state = result
    state["user_message"] = "hmm"
    state["messages"].append(HumanMessage(content="hmm"))
    result = await graph.ainvoke(state, config=run_config, context=ctx)

    # Flow still active, confirmed slot not set (waiting for clear answer)
    assert len(result["flow_stack"]) == 1
    assert result["flow_slots"][flow_id].get("confirmed") is None
