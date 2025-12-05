"""Unit tests for NLU Pydantic models."""

import pytest
from pydantic import ValidationError

from soni.du.models import DialogueContext, MessageType, NLUOutput, SlotValue


def test_nlu_output_valid():
    """Test NLUOutput with valid data."""
    # Arrange & Act
    output = NLUOutput(
        message_type=MessageType.INTERRUPTION,
        command="book_flight",
        slots=[],
        confidence=0.95,
        reasoning="User explicitly states booking intent",
    )

    # Assert
    assert output.command == "book_flight"
    assert output.confidence == 0.95
    assert output.message_type == MessageType.INTERRUPTION


def test_nlu_output_confidence_validation():
    """Test NLUOutput validates confidence bounds."""
    # Arrange & Act & Assert
    with pytest.raises(ValidationError):
        NLUOutput(
            message_type=MessageType.INTERRUPTION,
            command="test",
            slots=[],
            confidence=1.5,  # Invalid: > 1.0
            reasoning="test",
        )


def test_nlu_output_confidence_negative():
    """Test NLUOutput rejects negative confidence."""
    # Arrange & Act & Assert
    with pytest.raises(ValidationError):
        NLUOutput(
            message_type=MessageType.INTERRUPTION,
            command="test",
            slots=[],
            confidence=-0.1,  # Invalid: < 0.0
            reasoning="test",
        )


def test_slot_value_structure():
    """Test SlotValue with valid data."""
    # Arrange & Act
    slot = SlotValue(name="origin", value="Madrid", confidence=0.9)

    # Assert
    assert slot.name == "origin"
    assert slot.value == "Madrid"
    assert slot.confidence == 0.9


def test_slot_value_confidence_validation():
    """Test SlotValue validates confidence bounds."""
    # Arrange & Act & Assert
    with pytest.raises(ValidationError):
        SlotValue(
            name="origin",
            value="Madrid",
            confidence=1.5,  # Invalid: > 1.0
        )


def test_dialogue_context_defaults():
    """Test DialogueContext has proper defaults."""
    # Arrange & Act
    context = DialogueContext()

    # Assert
    assert context.current_flow == "none"
    assert len(context.available_actions) == 0
    assert len(context.available_flows) == 0
    assert len(context.current_slots) == 0
    assert len(context.expected_slots) == 0


def test_dialogue_context_custom_values():
    """Test DialogueContext with custom values."""
    # Arrange & Act
    context = DialogueContext(
        current_flow="book_flight",
        available_actions=["book_flight", "search_flights"],
        current_slots={"origin": "Madrid"},
    )

    # Assert
    assert context.current_flow == "book_flight"
    assert len(context.available_actions) == 2
    assert context.current_slots["origin"] == "Madrid"


def test_message_type_enum():
    """Test MessageType enum values."""
    # Arrange & Act
    types = [
        MessageType.SLOT_VALUE,
        MessageType.CORRECTION,
        MessageType.MODIFICATION,
        MessageType.INTERRUPTION,
        MessageType.DIGRESSION,
        MessageType.CLARIFICATION,
        MessageType.CANCELLATION,
        MessageType.CONFIRMATION,
        MessageType.CONTINUATION,
    ]

    # Assert
    assert len(types) == 9
    assert MessageType.INTERRUPTION.value == "interruption"


def test_nlu_output_with_slots():
    """Test NLUOutput with slot values."""
    # Arrange & Act
    output = NLUOutput(
        message_type=MessageType.SLOT_VALUE,
        command="book_flight",
        slots=[
            SlotValue(name="origin", value="Madrid", confidence=0.9),
            SlotValue(name="destination", value="Barcelona", confidence=0.9),
        ],
        confidence=0.9,
        reasoning="User provides origin and destination",
    )

    # Assert
    assert len(output.slots) == 2
    assert output.slots[0].name == "origin"
    assert output.slots[1].name == "destination"
