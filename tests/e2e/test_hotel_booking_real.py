import os

import pytest
from langgraph.checkpoint.memory import MemorySaver

# Import handlers
import examples.hotel_booking.handlers  # noqa: F401
from soni.config.loader import ConfigLoader
from soni.runtime.loop import RuntimeLoop


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_room_booking_with_preferences():
    """Test hotel booking with room preferences."""
    if not os.getenv("OPENAI_API_KEY"):
        pytest.skip("OPENAI_API_KEY not set")

    config = ConfigLoader.load("examples/hotel_booking/domain")
    config.settings.rephrase_responses = False

    checkpointer = MemorySaver()
    async with RuntimeLoop(config, checkpointer=checkpointer) as runtime:
        session_id = "hotel-test-001"

        # 1. Start
        response = await runtime.process_message("I want to book a room", user_id=session_id)
        assert "city" in response.lower() or "where" in response.lower()

        # 2. Location & Dates (provide multiple slots at once)
        response = await runtime.process_message(
            "In Barcelona from Jan 10 to Jan 15", user_id=session_id
        )
        assert "guests" in response.lower() or "room" in response.lower()

        # 3. Final slots
        response = await runtime.process_message("2 adults and a suite", user_id=session_id)
        assert "confirmed" in response.lower() or "booked" in response.lower()


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_booking_cancellation():
    """Test canceling a booking."""
    if not os.getenv("OPENAI_API_KEY"):
        pytest.skip("OPENAI_API_KEY not set")

    config = ConfigLoader.load("examples/hotel_booking/domain")
    config.settings.rephrase_responses = False

    checkpointer = MemorySaver()
    async with RuntimeLoop(config, checkpointer=checkpointer) as runtime:
        session_id = "hotel-test-002"

        await runtime.process_message("Book a room in Madrid", user_id=session_id)
        response = await runtime.process_message("Cancel everything", user_id=session_id)

        # Cancellation should return to idle or confirm cancellation
        assert "cancel" in response.lower() or "help" in response.lower()

        # Verify stack is empty
        state = await runtime._graph.aget_state(
            {"configurable": {"thread_id": f"thread_{session_id}"}}
        )
        assert not state.values.get("flow_stack")
