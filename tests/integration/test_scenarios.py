from unittest.mock import AsyncMock, Mock

import pytest
from langgraph.checkpoint.memory import MemorySaver

from soni.config import FlowConfig, SoniConfig
from soni.config.steps import CollectStepConfig, ConfirmStepConfig, SayStepConfig
from soni.core.commands import SetSlot, StartFlow
from soni.du.models import NLUOutput
from soni.runtime.loop import RuntimeLoop


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


@pytest.fixture
def runtime(scenario_config):
    """Runtime with mocked DU."""
    checkpointer = MemorySaver()
    rt = RuntimeLoop(scenario_config, checkpointer=checkpointer, du=Mock())
    return rt


@pytest.mark.skip(
    reason="TODO: Rewrite using graph.ainvoke like test_auto_resume - process_message returns str not state"
)
@pytest.mark.asyncio
async def test_scenario_interruption_and_resume(runtime):
    """
    Scenario:
    1. User starts 'book_flight' -> System asks "Where to?"
    2. User says "what's the weather in London?" (INTERRUPTION)
    3. System handles weather, then resumes booking

    With interrupt() API: verify flow stack changes and slot values
    """
    await runtime.initialize()

    # Mock NLU
    runtime.du.acall.side_effect = [
        # Turn 1: book flight
        NLUOutput(commands=[StartFlow(flow_name="book_flight")]),
        # Turn 2: weather in London (interruption while collecting destination)
        NLUOutput(
            commands=[StartFlow(flow_name="check_weather"), SetSlot(slot="city", value="London")]
        ),
        # Turn 3: Paris (resume booking, provide destination)
        NLUOutput(commands=[SetSlot(slot="destination", value="Paris")]),
    ]

    # Turn 1: Start booking
    state = await runtime.aprocess_turn("book a flight", thread_id="t1")

    # Verify: booking flow started
    assert len(state["flow_stack"]) == 1
    assert state["flow_stack"][0]["flow_name"] == "book_flight"

    # Turn 2: Weather interruption + intent change
    state = await runtime.aprocess_turn("what's the weather in London?", thread_id="t1")

    # Verify: weather flow on top, London slot set
    assert len(state["flow_stack"]) == 2
    assert state["flow_stack"][1]["flow_name"] == "check_weather"
    weather_flow_id = state["flow_stack"][1]["flow_id"]
    assert state["flow_slots"][weather_flow_id].get("city") == "London"
    # Should have weather message
    assert any("Sunny" in str(m.content) for m in state["messages"])

    # Turn 3: Resume booking with "Paris"
    state = await runtime.aprocess_turn("Paris", thread_id="t1")

    # Verify: back to booking flow (weather completed)
    assert len(state["flow_stack"]) == 1
    assert state["flow_stack"][0]["flow_name"] == "book_flight"
    booking_flow_id = state["flow_stack"][0]["flow_id"]
    assert state["flow_slots"][booking_flow_id]["destination"] == "Paris"


@pytest.mark.asyncio
async def test_scenario_correction(runtime):
    """
    Scenario:
    1. User starts 'book_flight'
    2. User provides destination "Paris"
    3. User corrects "No, I meant London"
    4. System updates slot to "London"
    """
    await runtime.initialize()

    # 1. Start
    runtime.du.acall = AsyncMock(
        return_value=NLUOutput(commands=[StartFlow(flow_name="book_flight")])
    )
    await runtime.process_message("Book flight", user_id="user_corr")

    # 2. Provide Paris
    runtime.du.acall = AsyncMock(
        return_value=NLUOutput(commands=[SetSlot(slot="destination", value="Paris")])
    )
    resp2 = await runtime.process_message("Paris", user_id="user_corr")
    assert "When?" in resp2  # Moved to next step

    # 3. Correct to London
    runtime.du.acall = AsyncMock(
        return_value=NLUOutput(commands=[SetSlot(slot="destination", value="London")])
    )
    await runtime.process_message("No, London", user_id="user_corr")

    # Verify slot value in state
    state = await runtime.get_state("user_corr")
    greeting_flow = next(f for f in state["flow_stack"] if f["flow_name"] == "book_flight")
    flow_id = greeting_flow["flow_id"]
    assert state["flow_slots"][flow_id]["destination"] == "London"


@pytest.mark.skip(
    reason="TODO: Rewrite using graph.ainvoke like test_auto_resume - process_message returns str not state"
)
@pytest.mark.asyncio
async def test_scenario_denial_cancel(runtime):
    """
    Scenario:
    1. Book flight to Paris Tomorrow
    2. System asks confirmation
    3. User denies -> Should proceed with denial (confirmation = False)

    With interrupt() API: verify confirmation denial behavior
    """
    await runtime.initialize()

    runtime.du.acall.side_effect = [
        # Turn 1: book flight with all slots
        NLUOutput(
            commands=[
                StartFlow(flow_name="book_flight"),
                SetSlot(slot="destination", value="Paris"),
                SetSlot(slot="date", value="Tomorrow"),
            ]
        ),
        # Turn 2: deny confirmation
        NLUOutput(commands=[]),  # No affirm/deny command -> will call interrupt()
    ]

    # Turn 1: Book with all info
    state = await runtime.aprocess_turn("book flight to Paris tomorrow", thread_id="t2")

    # Verify: flow started, slots collected
    assert len(state["flow_stack"]) == 1
    flow_id = state["flow_stack"][0]["flow_id"]
    assert state["flow_slots"][flow_id]["destination"] == "Paris"
    assert state["flow_slots"][flow_id]["date"] == "Tomorrow"

    # Turn 2: No affirm/deny -> should call interrupt for confirmation
    state = await runtime.aprocess_turn("hmm", thread_id="t2")

    # With interrupt(): confirm node will interrupt and wait
    # The flow should still be active, waiting for confirmation
    assert len(state["flow_stack"]) == 1
    # Confirmed slot should not be set yet
    assert state["flow_slots"][flow_id].get("confirmed") is None
