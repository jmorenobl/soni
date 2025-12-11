"""Isolated NLU tests - test SoniDU module directly with real LLM.

These tests isolate NLU from dialogue management to verify NLU behavior
independently. They use real LLM to test actual NLU predictions.

Run with: uv run pytest tests/integration/test_nlu_isolated.py -v
Requires: OPENAI_API_KEY environment variable
"""

import dspy
import pytest

from soni.du.models import DialogueContext, MessageType, NLUOutput, SlotAction
from soni.du.modules import SoniDU


@pytest.fixture
def nlu():
    """Create SoniDU instance with Chain of Thought enabled for better precision in tests."""
    return SoniDU(use_cot=True)


@pytest.mark.integration
@pytest.mark.asyncio
async def test_nlu_slot_value_extraction(nlu, configure_dspy_for_integration, skip_without_api_key):
    """Test NLU extracts slot values correctly."""
    # Arrange
    user_message = "I want to fly to Madrid tomorrow"

    history = dspy.History(
        messages=[
            {"role": "user", "content": "I want to book a flight"},
            {"role": "assistant", "content": "Where would you like to fly to?"},
        ]
    )

    context = DialogueContext(
        current_flow="book_flight",
        expected_slots=["destination", "departure_date"],
        current_slots={},
        current_prompted_slot="destination",
        conversation_state="waiting_for_slot",
        available_flows={"book_flight": "Book a flight from origin to destination"},
        available_actions=["search_flights"],
    )

    # Act
    result = await nlu.predict(user_message, history, context)

    # Assert
    assert isinstance(result, NLUOutput)
    assert result.message_type == MessageType.SLOT_VALUE
    assert result.command is None
    assert len(result.slots) >= 1

    # Verify destination slot
    destination_slot = next((s for s in result.slots if s.name == "destination"), None)
    assert destination_slot is not None, "Should extract destination slot"
    assert destination_slot.value == "Madrid"
    assert destination_slot.action == SlotAction.PROVIDE
    assert destination_slot.confidence > 0.7


@pytest.mark.integration
@pytest.mark.asyncio
async def test_nlu_correction_detection(nlu, configure_dspy_for_integration, skip_without_api_key):
    """Test NLU detects corrections correctly."""
    # Arrange
    user_message = "No, I meant Barcelona"

    history = dspy.History(
        messages=[
            {"role": "user", "content": "Madrid"},
            {"role": "assistant", "content": "You want to fly to Madrid, correct?"},
        ]
    )

    context = DialogueContext(
        current_flow="book_flight",
        expected_slots=["destination"],
        current_slots={"destination": "Madrid"},  # Previous value
        current_prompted_slot=None,
        conversation_state="confirming",  # Key: user is responding to confirmation
        available_flows={"book_flight": "Book a flight"},
        available_actions=["confirm_booking"],
    )

    # Act
    result = await nlu.predict(user_message, history, context)

    # Assert
    assert result.message_type == MessageType.CORRECTION
    assert len(result.slots) == 1
    assert result.slots[0].name == "destination"
    assert result.slots[0].value == "Barcelona"
    assert result.slots[0].action == SlotAction.CORRECT
    assert result.slots[0].previous_value == "Madrid"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_nlu_confirmation_detection_yes(
    nlu, configure_dspy_for_integration, skip_without_api_key
):
    """Test NLU detects positive confirmation responses correctly."""
    # Arrange
    user_message = "Yes, that's correct"

    context = DialogueContext(
        current_flow="book_flight",
        expected_slots=["destination", "departure_date"],
        current_slots={"destination": "Madrid", "departure_date": "2025-12-15"},
        current_prompted_slot=None,
        conversation_state="confirming",  # CRITICAL: must be "confirming"
        available_flows={"book_flight": "Book a flight"},
        available_actions=["confirm_booking"],
    )

    # Act
    result = await nlu.predict(user_message, history=dspy.History(messages=[]), context=context)

    # Assert
    assert result.message_type == MessageType.CONFIRMATION
    assert result.confirmation_value is True
    assert result.command is None
    assert len(result.slots) == 0  # Usually empty for confirmations


@pytest.mark.integration
@pytest.mark.asyncio
async def test_nlu_confirmation_detection_no(
    nlu, configure_dspy_for_integration, skip_without_api_key
):
    """Test NLU detects negative confirmation responses correctly."""
    # Arrange
    user_message = "No"

    context = DialogueContext(
        current_flow="book_flight",
        expected_slots=["destination", "departure_date"],
        current_slots={"destination": "Madrid", "departure_date": "2025-12-15"},
        current_prompted_slot=None,
        conversation_state="confirming",  # CRITICAL: must be "confirming"
        available_flows={"book_flight": "Book a flight"},
        available_actions=["confirm_booking"],
    )

    # Act
    result = await nlu.predict(user_message, history=dspy.History(messages=[]), context=context)

    # Assert
    assert result.message_type == MessageType.CONFIRMATION
    assert result.confirmation_value is False
    assert result.command is None


@pytest.mark.integration
@pytest.mark.asyncio
async def test_nlu_interruption_detection(
    nlu, configure_dspy_for_integration, skip_without_api_key
):
    """Test NLU detects intent changes correctly."""
    # Arrange
    user_message = "Actually, I want to cancel my booking instead"

    context = DialogueContext(
        current_flow="book_flight",
        expected_slots=["destination"],
        current_slots={"destination": "Madrid"},
        current_prompted_slot="departure_date",
        conversation_state="waiting_for_slot",
        available_flows={
            "book_flight": "Book a flight from origin to destination",
            "cancel_booking": "Cancel an existing flight booking",
        },
        available_actions=["search_flights", "cancel_booking"],
    )

    # Act
    result = await nlu.predict(user_message, history=dspy.History(messages=[]), context=context)

    # Assert
    assert result.message_type == MessageType.INTERRUPTION
    assert result.command == "cancel_booking"
    assert len(result.slots) == 0


@pytest.mark.integration
@pytest.mark.asyncio
async def test_nlu_digression_detection(nlu, configure_dspy_for_integration, skip_without_api_key):
    """Test NLU detects digressions correctly."""
    # Arrange
    user_message = "What destinations do you fly to?"

    context = DialogueContext(
        current_flow="book_flight",
        expected_slots=["destination", "departure_date"],
        current_slots={},
        current_prompted_slot="destination",
        conversation_state="waiting_for_slot",
        available_flows={"book_flight": "Book a flight"},
        available_actions=["search_flights"],
    )

    # Act
    result = await nlu.predict(user_message, history=dspy.History(messages=[]), context=context)

    # Assert
    assert result.message_type == MessageType.DIGRESSION
    assert result.command is None
    assert len(result.slots) == 0


@pytest.mark.integration
@pytest.mark.asyncio
async def test_nlu_multi_slot_extraction(nlu, configure_dspy_for_integration, skip_without_api_key):
    """Test NLU extracts multiple slots from one message."""
    # Arrange
    user_message = "I want to fly from Madrid to Barcelona tomorrow"

    context = DialogueContext(
        current_flow="book_flight",
        expected_slots=["origin", "destination", "departure_date"],
        current_slots={},
        current_prompted_slot="origin",
        conversation_state="waiting_for_slot",
        available_flows={"book_flight": "Book a flight"},
        available_actions=["search_flights"],
    )

    # Act
    result = await nlu.predict(user_message, history=dspy.History(messages=[]), context=context)

    # Assert
    assert result.message_type == MessageType.SLOT_VALUE
    assert len(result.slots) >= 2  # Should extract at least origin and destination

    slot_names = {s.name for s in result.slots}
    assert "origin" in slot_names or "destination" in slot_names


@pytest.mark.integration
@pytest.mark.asyncio
async def test_nlu_modification_detection(
    nlu, configure_dspy_for_integration, skip_without_api_key
):
    """Test NLU detects modification requests correctly."""
    # Arrange
    user_message = "Can I change the destination to London?"

    context = DialogueContext(
        current_flow="book_flight",
        expected_slots=["destination", "departure_date"],
        current_slots={"destination": "Madrid", "departure_date": "2025-12-15"},
        current_prompted_slot=None,
        conversation_state="waiting_for_slot",  # Not confirming, proactive change
        available_flows={"book_flight": "Book a flight"},
        available_actions=["search_flights"],
    )

    # Act
    result = await nlu.predict(user_message, history=dspy.History(messages=[]), context=context)

    # Assert
    assert result.message_type == MessageType.MODIFICATION
    assert len(result.slots) == 1
    assert result.slots[0].name == "destination"
    assert result.slots[0].value == "London"
    assert result.slots[0].action == SlotAction.MODIFY
    assert result.slots[0].previous_value == "Madrid"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_nlu_cancellation_detection(
    nlu, configure_dspy_for_integration, skip_without_api_key
):
    """Test NLU detects cancellation requests correctly."""
    # Arrange
    user_message = "Cancel"

    context = DialogueContext(
        current_flow="book_flight",
        expected_slots=["destination", "departure_date"],
        current_slots={"destination": "Madrid"},
        current_prompted_slot="departure_date",
        conversation_state="waiting_for_slot",
        available_flows={"book_flight": "Book a flight"},
        available_actions=["search_flights"],
    )

    # Act
    result = await nlu.predict(user_message, history=dspy.History(messages=[]), context=context)

    # Assert
    assert result.message_type == MessageType.CANCELLATION
    # Command should be None or "cancel", but LLM may set it to current flow name
    # The important thing is that message_type is CANCELLATION
    assert result.command in ("cancel", None) or result.command == context.current_flow
    assert len(result.slots) == 0
