"""Integration tests for Dialogue Understanding module with real LLM.

Tests NLU Command-Driven output with actual LLM predictions.
Requires OPENAI_API_KEY environment variable.
"""

import dspy
import pytest

from soni.core.commands import SetSlot, StartFlow
from soni.du.models import DialogueContext, NLUOutput
from soni.du.modules import SoniDU


@pytest.mark.integration
@pytest.mark.asyncio
async def test_soni_du_basic_start_flow(configure_dspy_for_integration, skip_without_api_key):
    """
    Test NLU produces StartFlow command for new flow trigger.

    Requires OPENAI_API_KEY environment variable.
    """
    # Arrange
    nlu = SoniDU()
    user_message = "I want to book a flight to Paris"

    history = dspy.History(messages=[])
    context = DialogueContext(
        current_flow="none",
        expected_slots=["origin", "destination", "departure_date"],
        current_slots={},
        current_prompted_slot=None,
        conversation_state=None,
        available_flows={"book_flight": "Book a flight from origin to destination"},
        available_actions=["book_flight", "search_flights", "help"],
    )

    # Act
    result = await nlu.predict(user_message, history, context)

    # Assert
    assert isinstance(result, NLUOutput)
    assert result.confidence > 0.0
    assert len(result.commands) > 0

    # Should have StartFlow command for book_flight
    start_flow_cmds = [c for c in result.commands if isinstance(c, StartFlow)]
    assert len(start_flow_cmds) >= 1, f"Expected StartFlow, got: {result.commands}"
    assert start_flow_cmds[0].flow_name == "book_flight"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_soni_du_slot_extraction(configure_dspy_for_integration, skip_without_api_key):
    """
    Test NLU produces SetSlot command for slot value.

    Requires OPENAI_API_KEY environment variable.
    """
    # Arrange
    nlu = SoniDU()
    user_message = "Paris"

    history = dspy.History(
        messages=[
            {"role": "assistant", "content": "Where would you like to fly to?"},
        ]
    )
    context = DialogueContext(
        current_flow="book_flight",
        expected_slots=["origin", "destination", "departure_date"],
        current_slots={"origin": "Madrid"},
        current_prompted_slot="destination",
        conversation_state="waiting_for_slot",
        available_flows={},
        available_actions=[],
    )

    # Act
    result = await nlu.predict(user_message, history, context)

    # Assert
    assert isinstance(result, NLUOutput)
    assert len(result.commands) > 0

    # Should have SetSlot for destination
    set_slot_cmds = [c for c in result.commands if isinstance(c, SetSlot)]
    assert len(set_slot_cmds) >= 1, f"Expected SetSlot, got: {result.commands}"
    assert set_slot_cmds[0].slot_name == "destination"
    assert "paris" in set_slot_cmds[0].value.lower()
