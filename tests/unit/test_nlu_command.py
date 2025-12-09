"""Test NLU command field generation."""

import dspy
import pytest
from dspy.utils.dummies import DummyLM

from soni.du.models import DialogueContext, MessageType, NLUOutput, SlotValue
from soni.du.modules import SoniDU


@pytest.fixture
def dummy_lm_slot_value():
    """Create DummyLM that returns slot_value with command=None."""
    lm = DummyLM(
        [
            {
                "result": {
                    "message_type": "slot_value",
                    "command": None,
                    "slots": [
                        {
                            "name": "origin",
                            "value": "Madrid",
                            "confidence": 0.95,
                            "action": "provide",
                        }
                    ],
                    "confidence": 0.95,
                },
            }
        ]
    )
    dspy.configure(lm=lm)
    return lm


@pytest.fixture
def dummy_lm_intent_change():
    """Create DummyLM that returns intent_change with command set."""
    lm = DummyLM(
        [
            {
                "result": {
                    "message_type": "interruption",
                    "command": "book_flight",
                    "slots": [],
                    "confidence": 0.90,
                },
            }
        ]
    )
    dspy.configure(lm=lm)
    return lm


@pytest.fixture
def dummy_lm_cancellation():
    """Create DummyLM that returns cancellation with command='cancel'."""
    lm = DummyLM(
        [
            {
                "result": {
                    "message_type": "cancellation",
                    "command": "cancel",
                    "slots": [],
                    "confidence": 0.95,
                },
            }
        ]
    )
    dspy.configure(lm=lm)
    return lm


@pytest.mark.asyncio
async def test_command_is_none_for_slot_value(dummy_lm_slot_value):
    """Command should be None when user provides slot value."""
    # Setup
    nlu = SoniDU(use_cot=False)

    # Context: waiting for origin
    context = DialogueContext(
        current_flow="book_flight",
        expected_slots=["origin", "destination", "departure_date"],
        current_prompted_slot="origin",
    )
    history = dspy.History(messages=[])

    # Act
    result = await nlu.predict("Madrid", history, context)

    # Assert
    assert result.message_type == MessageType.SLOT_VALUE
    assert result.command is None  # Must be None!
    assert len(result.slots) == 1
    assert result.slots[0].name == "origin"
    assert result.slots[0].value == "Madrid"


@pytest.mark.asyncio
async def test_command_is_set_for_intent_change(dummy_lm_intent_change):
    """Command should be flow name when user changes intent."""
    # Setup
    nlu = SoniDU(use_cot=False)

    # Context: no active flow
    context = DialogueContext(
        current_flow="none",
        available_flows={"book_flight": "Book a flight", "check_booking": "Check booking"},
    )
    history = dspy.History(messages=[])

    # Act
    result = await nlu.predict("I want to book a flight", history, context)

    # Assert
    assert result.command == "book_flight"  # Must be set!
    assert result.message_type == MessageType.INTERRUPTION


@pytest.mark.asyncio
async def test_command_is_cancel_for_cancellation(dummy_lm_cancellation):
    """Command should be 'cancel' for cancellation."""
    # Setup
    nlu = SoniDU(use_cot=False)

    context = DialogueContext(current_flow="book_flight")
    history = dspy.History(messages=[])

    # Act
    result = await nlu.predict("cancel", history, context)

    # Assert
    assert result.message_type == MessageType.CANCELLATION
    assert result.command == "cancel"  # Must be 'cancel'!


def test_nlu_output_command_can_be_none():
    """Test that NLUOutput can be created with command=None."""
    # Arrange & Act
    output = NLUOutput(
        message_type=MessageType.SLOT_VALUE,
        command=None,
        slots=[SlotValue(name="origin", value="Madrid", confidence=0.95)],
        confidence=0.95,
    )

    # Assert
    assert output.command is None
    assert output.message_type == MessageType.SLOT_VALUE


def test_nlu_output_command_defaults_to_none():
    """Test that NLUOutput command defaults to None when not provided."""
    # Arrange & Act
    output = NLUOutput(
        message_type=MessageType.SLOT_VALUE,
        slots=[],
        confidence=0.95,
    )

    # Assert
    assert output.command is None


def test_nlu_output_command_can_be_string():
    """Test that NLUOutput can still have command as string."""
    # Arrange & Act
    output = NLUOutput(
        message_type=MessageType.INTERRUPTION,
        command="book_flight",
        slots=[],
        confidence=0.90,
    )

    # Assert
    assert output.command == "book_flight"
    assert isinstance(output.command, str)
