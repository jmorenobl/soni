"""Integration tests for Dialogue Understanding module with real LLM."""

import dspy
import pytest

from soni.du.models import DialogueContext, MessageType, NLUOutput
from soni.du.modules import SoniDU


@pytest.mark.integration
@pytest.mark.asyncio
async def test_soni_du_integration_real_dspy(configure_dspy_for_integration, skip_without_api_key):
    """
    Integration test with real DSPy LM (requires API key).

    This test runs with integration tests: make test-integration

    Requires OPENAI_API_KEY environment variable.
    """
    # Arrange
    nlu = SoniDU()
    user_message = "I want to book a flight to Paris"

    history = dspy.History(messages=[])
    context = DialogueContext(
        current_flow="none",
        expected_slots=[],
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
    assert result.message_type in (MessageType.INTERRUPTION, MessageType.SLOT_VALUE)
    assert result.confidence > 0.0
    # If interruption, should have command
    if result.message_type == MessageType.INTERRUPTION:
        assert result.command == "book_flight"
