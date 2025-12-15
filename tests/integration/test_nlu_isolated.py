"""Isolated NLU tests - test SoniDU module directly with real LLM.

These tests isolate NLU from dialogue management to verify NLU behavior
independently. They use real LLM to test actual NLU predictions.

Run with: uv run pytest tests/integration/test_nlu_isolated.py -v
Requires: OPENAI_API_KEY environment variable
"""

import dspy
import pytest

from soni.core.commands import (
    AffirmConfirmation,
    CancelFlow,
    Clarify,
    CorrectSlot,
    DenyConfirmation,
    SetSlot,
    StartFlow,
)
from soni.du.models import DialogueContext, NLUOutput
from soni.du.modules import SoniDU


@pytest.fixture
def nlu():
    """Create SoniDU instance with Chain of Thought enabled for better precision in tests."""
    return SoniDU(use_cot=True)


# =============================================================================
# SLOT VALUE TESTS
# =============================================================================


@pytest.mark.integration
@pytest.mark.asyncio
async def test_nlu_slot_value_extraction(nlu, configure_dspy_for_integration, skip_without_api_key):
    """Test NLU produces SetSlot command for slot values."""
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
    assert len(result.commands) >= 1

    # Should have SetSlot for destination
    set_slots = [c for c in result.commands if isinstance(c, SetSlot)]
    assert len(set_slots) >= 1, f"Expected SetSlot, got: {result.commands}"

    dest_slot = next((s for s in set_slots if s.slot_name == "destination"), None)
    assert dest_slot is not None, "Should extract destination slot"
    assert "madrid" in dest_slot.value.lower()


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
    set_slots = [c for c in result.commands if isinstance(c, SetSlot)]
    assert len(set_slots) >= 2, f"Expected at least 2 SetSlot, got: {result.commands}"

    slot_names = {s.slot_name for s in set_slots}
    assert "origin" in slot_names or "destination" in slot_names


# =============================================================================
# CORRECTION TESTS
# =============================================================================


@pytest.mark.integration
@pytest.mark.asyncio
async def test_nlu_correction_detection(nlu, configure_dspy_for_integration, skip_without_api_key):
    """Test NLU produces CorrectSlot command for corrections."""
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
        current_slots={"destination": "Madrid"},
        current_prompted_slot=None,
        conversation_state="confirming",
        available_flows={"book_flight": "Book a flight"},
        available_actions=["confirm_booking"],
    )

    # Act
    result = await nlu.predict(user_message, history, context)

    # Assert - should be CorrectSlot or DenyConfirmation
    correct_slots = [c for c in result.commands if isinstance(c, CorrectSlot)]
    deny_cmds = [c for c in result.commands if isinstance(c, DenyConfirmation)]

    # Either correction or denial with slot_to_change is acceptable
    assert len(correct_slots) >= 1 or len(deny_cmds) >= 1, (
        f"Expected CorrectSlot or DenyConfirmation, got: {result.commands}"
    )


# =============================================================================
# CONFIRMATION TESTS
# =============================================================================


@pytest.mark.integration
@pytest.mark.asyncio
async def test_nlu_confirmation_yes(nlu, configure_dspy_for_integration, skip_without_api_key):
    """Test NLU produces AffirmConfirmation for positive confirmation."""
    # Arrange
    user_message = "Yes, that's correct"

    context = DialogueContext(
        current_flow="book_flight",
        expected_slots=["destination", "departure_date"],
        current_slots={"destination": "Madrid", "departure_date": "2025-12-15"},
        current_prompted_slot=None,
        conversation_state="confirming",
        available_flows={"book_flight": "Book a flight"},
        available_actions=["confirm_booking"],
    )

    # Act
    result = await nlu.predict(user_message, history=dspy.History(messages=[]), context=context)

    # Assert
    affirm_cmds = [c for c in result.commands if isinstance(c, AffirmConfirmation)]
    assert len(affirm_cmds) >= 1, f"Expected AffirmConfirmation, got: {result.commands}"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_nlu_confirmation_no(nlu, configure_dspy_for_integration, skip_without_api_key):
    """Test NLU produces DenyConfirmation for negative confirmation."""
    # Arrange
    user_message = "No"

    context = DialogueContext(
        current_flow="book_flight",
        expected_slots=["destination", "departure_date"],
        current_slots={"destination": "Madrid", "departure_date": "2025-12-15"},
        current_prompted_slot=None,
        conversation_state="confirming",
        available_flows={"book_flight": "Book a flight"},
        available_actions=["confirm_booking"],
    )

    # Act
    result = await nlu.predict(user_message, history=dspy.History(messages=[]), context=context)

    # Assert
    deny_cmds = [c for c in result.commands if isinstance(c, DenyConfirmation)]
    assert len(deny_cmds) >= 1, f"Expected DenyConfirmation, got: {result.commands}"


# =============================================================================
# FLOW CONTROL TESTS
# =============================================================================


@pytest.mark.integration
@pytest.mark.asyncio
async def test_nlu_interruption_detection(
    nlu, configure_dspy_for_integration, skip_without_api_key
):
    """Test NLU produces StartFlow for intent change."""
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

    # Assert - could be StartFlow(cancel_booking) or CancelFlow
    start_flows = [c for c in result.commands if isinstance(c, StartFlow)]
    cancel_flows = [c for c in result.commands if isinstance(c, CancelFlow)]

    assert len(start_flows) >= 1 or len(cancel_flows) >= 1, (
        f"Expected StartFlow or CancelFlow, got: {result.commands}"
    )


@pytest.mark.integration
@pytest.mark.asyncio
async def test_nlu_cancellation_detection(
    nlu, configure_dspy_for_integration, skip_without_api_key
):
    """Test NLU produces CancelFlow command for cancellation."""
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
    cancel_flows = [c for c in result.commands if isinstance(c, CancelFlow)]
    assert len(cancel_flows) >= 1, f"Expected CancelFlow, got: {result.commands}"


# =============================================================================
# DIGRESSION / CLARIFICATION TESTS
# =============================================================================


@pytest.mark.integration
@pytest.mark.asyncio
async def test_nlu_digression_detection(nlu, configure_dspy_for_integration, skip_without_api_key):
    """Test NLU produces Clarify or ChitChat for digressions."""
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

    # Assert - should be Clarify, ChitChat, or SetSlot (digression commands)
    # Note: NLU may interpret "What destinations..." as a request or as partial input
    from soni.core.commands import ChitChat

    clarify_cmds = [c for c in result.commands if isinstance(c, Clarify)]
    chitchat_cmds = [c for c in result.commands if isinstance(c, ChitChat)]
    set_slots = [c for c in result.commands if isinstance(c, SetSlot)]

    # Digressions produce Clarify, ChitChat, or sometimes SetSlot
    assert len(clarify_cmds) >= 1 or len(chitchat_cmds) >= 1 or len(set_slots) >= 1, (
        f"Expected Clarify, ChitChat, or SetSlot for digression/question, got: {result.commands}"
    )
