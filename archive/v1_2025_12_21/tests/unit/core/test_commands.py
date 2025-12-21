"""Unit tests for Command hierarchy."""

import pytest

from soni.core.commands import (
    CancelFlow,
    Command,
    SetSlot,
    StartFlow,
    parse_command,
)


class TestStartFlowCommand:
    """Tests for StartFlow command."""

    def test_start_flow_has_correct_command_type(self):
        """
        GIVEN a StartFlow command
        WHEN command_type is accessed
        THEN returns 'start_flow'
        """
        # Arrange & Act
        cmd = StartFlow(flow_name="book_flight")

        # Assert
        assert cmd.type == "start_flow"
        assert cmd.flow_name == "book_flight"

    def test_start_flow_with_initial_slots(self):
        """
        GIVEN a StartFlow command with slots
        WHEN created
        THEN slots are stored correctly
        """
        # Arrange & Act
        cmd = StartFlow(flow_name="book_flight", slots={"destination": "Paris"})

        # Assert
        assert cmd.slots["destination"] == "Paris"

    def test_start_flow_serialization(self):
        """
        GIVEN a StartFlow command
        WHEN serialized to dict
        THEN can be deserialized back
        """
        # Arrange
        cmd = StartFlow(flow_name="book_flight", slots={"origin": "NYC"})

        # Act
        data = cmd.model_dump()
        restored = parse_command(data)

        # Assert
        assert isinstance(restored, StartFlow)
        assert restored.flow_name == "book_flight"


class TestSetSlotCommand:
    """Tests for SetSlot command."""

    def test_set_slot_stores_value_and_confidence(self):
        """
        GIVEN a SetSlot command
        WHEN created with value and confidence
        THEN both are stored
        """
        # Arrange & Act
        cmd = SetSlot(slot="origin", value="Madrid", confidence=0.95)

        # Assert
        assert cmd.slot == "origin"
        assert cmd.value == "Madrid"
        assert cmd.confidence == 0.95


class TestParseCommand:
    """Tests for parse_command function."""

    def test_parse_unknown_command_raises_value_error(self):
        """
        GIVEN a dict with unknown command type
        WHEN parsed
        THEN raises ValueError
        """
        # Arrange
        data = {"type": "unknown_type", "foo": "bar"}

        # Act & Assert
        with pytest.raises(ValueError, match="Unknown command"):
            parse_command(data)

    def test_parse_base_command_fails_if_not_registered(self):
        """
        GIVEN a base command
        WHEN parsed
        THEN raises ValueError because base Command is usually not registered or abstract
        """
        # Note: Command base class usually doesn't register itself under 'base' unless explicitly set
        # This test ensures we only allow specific registered commands
        data = {"type": "base"}
        with pytest.raises(ValueError):
            parse_command(data)
