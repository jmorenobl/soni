"""Unit tests for Command models."""

import pytest
from pydantic import ValidationError

from soni.core.commands import (
    AffirmConfirmation,
    CancelFlow,
    ChitChat,
    Clarify,
    Command,
    CorrectSlot,
    DenyConfirmation,
    HumanHandoff,
    OutOfScope,
    SetSlot,
    StartFlow,
)


def test_command_base():
    """Test base Command properties."""
    cmd = Command(confidence=0.8)
    assert cmd.confidence == 0.8
    assert str(cmd) == "Command"

    # Test validator
    with pytest.raises(ValidationError):
        Command(confidence=1.5)


def test_start_flow_command():
    """Test StartFlow command."""
    cmd = StartFlow(flow_name="book_flight", slots={"destination": "Madrid"})
    assert cmd.flow_name == "book_flight"
    assert cmd.slots == {"destination": "Madrid"}
    assert isinstance(cmd, Command)


def test_set_slot_command():
    """Test SetSlot command."""
    cmd = SetSlot(slot_name="destination", value="Paris")
    assert cmd.slot_name == "destination"
    assert cmd.value == "Paris"


def test_correct_slot_command():
    """Test CorrectSlot command."""
    cmd = CorrectSlot(slot_name="destination", new_value="London")
    assert cmd.slot_name == "destination"
    assert cmd.new_value == "London"


def test_confirmation_commands():
    """Test Affirm/Deny commands."""
    affirm = AffirmConfirmation()
    assert isinstance(affirm, Command)

    deny = DenyConfirmation(slot_to_change="date")
    assert deny.slot_to_change == "date"


def test_clarify_command():
    """Test Clarify command."""
    cmd = Clarify(topic="fees", original_text="Are there fees?")
    assert cmd.topic == "fees"
    assert cmd.original_text == "Are there fees?"
