## Task: 002 - Command Hierarchy

**ID de tarea:** 002
**Hito:** 1 - Core Foundations
**Dependencias:** 001
**Duración estimada:** 4 horas

### Objetivo

Implement the Command hierarchy using Pydantic models. Commands are the contract between DU (Dialogue Understanding) and DM (Dialogue Manager).

### Contexto

Commands are the explicit abstraction layer that constrains the LLM's role to understanding only. The DM executes commands deterministically. This is a key architectural pattern from RASA CALM.

### Entregables

- [ ] `core/commands.py` with base Command class
- [ ] 10+ Command subclasses (StartFlow, SetSlot, Cancel, etc.)
- [ ] Serialization/deserialization methods
- [ ] Unit tests with 100% coverage

### Implementación Detallada

**Archivo:** `src/soni/core/commands.py`

```python
"""Command hierarchy for DU → DM communication.

Commands represent user intent in a structured form.
The DM executes these deterministically.
"""
from typing import Any, Literal
from pydantic import BaseModel, Field


class Command(BaseModel):
    """Base command from DU to DM.
    
    All commands must be serializable to dict for state storage.
    """
    
    command_type: str = Field(default="base")
    
    def model_dump_for_state(self) -> dict[str, Any]:
        """Serialize for storage in DialogueState."""
        return {"type": self.command_type, **self.model_dump(exclude={"command_type"})}


# Flow Control Commands

class StartFlow(Command):
    """Start a new flow."""
    
    command_type: Literal["start_flow"] = "start_flow"
    flow_name: str
    slots: dict[str, Any] = Field(default_factory=dict)


class CancelFlow(Command):
    """Cancel the current flow."""
    
    command_type: Literal["cancel_flow"] = "cancel_flow"
    reason: str | None = None


class CompleteFlow(Command):
    """Mark current flow as complete."""
    
    command_type: Literal["complete_flow"] = "complete_flow"


# Slot Commands

class SetSlot(Command):
    """Set a slot value."""
    
    command_type: Literal["set_slot"] = "set_slot"
    slot_name: str
    value: Any
    confidence: float = 1.0


class CorrectSlot(Command):
    """Correct a previously set slot."""
    
    command_type: Literal["correct_slot"] = "correct_slot"
    slot_name: str
    new_value: Any


class ClearSlot(Command):
    """Clear a slot value."""
    
    command_type: Literal["clear_slot"] = "clear_slot"
    slot_name: str


# Confirmation Commands

class AffirmConfirmation(Command):
    """User confirms (yes)."""
    
    command_type: Literal["affirm"] = "affirm"


class DenyConfirmation(Command):
    """User denies (no)."""
    
    command_type: Literal["deny"] = "deny"
    slot_to_change: str | None = None


# Conversation Commands

class RequestClarification(Command):
    """User requests clarification."""
    
    command_type: Literal["clarify"] = "clarify"
    topic: str | None = None


class ChitChat(Command):
    """Off-topic conversation."""
    
    command_type: Literal["chitchat"] = "chitchat"
    message: str | None = None


class HumanHandoff(Command):
    """Request human agent."""
    
    command_type: Literal["handoff"] = "handoff"
    reason: str | None = None


# Command parsing

def parse_command(data: dict[str, Any]) -> Command:
    """Parse a serialized command dict back to Command object."""
    command_type = data.get("type", "base")
    
    command_map = {
        "start_flow": StartFlow,
        "cancel_flow": CancelFlow,
        "complete_flow": CompleteFlow,
        "set_slot": SetSlot,
        "correct_slot": CorrectSlot,
        "clear_slot": ClearSlot,
        "affirm": AffirmConfirmation,
        "deny": DenyConfirmation,
        "clarify": RequestClarification,
        "chitchat": ChitChat,
        "handoff": HumanHandoff,
    }
    
    cls = command_map.get(command_type, Command)
    return cls(**{k: v for k, v in data.items() if k != "type"})
    return Command.parse(data)
```

### TDD Cycle (MANDATORY for new features)

#### Red Phase: Write Failing Tests

**Test file:** `tests/unit/core/test_commands.py`

```python
"""Unit tests for Command hierarchy."""
import pytest
from soni.core.commands import (
    Command, StartFlow, SetSlot, CancelFlow,
    AffirmConfirmation, DenyConfirmation,
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
        cmd = StartFlow(
            flow_name="book_flight",
            slots={"destination": "Paris"}
        )
        
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
        data = cmd.model_dump_for_state()
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
        cmd = SetSlot(slot_name="origin", value="Madrid", confidence=0.95)
        
        # Assert
        assert cmd.slot_name == "origin"
        assert cmd.value == "Madrid"
        assert cmd.confidence == 0.95


class TestParseCommand:
    """Tests for parse_command function."""

    def test_parse_unknown_command_returns_base(self):
        """
        GIVEN a dict with unknown command type
        WHEN parsed
        THEN returns base Command
        """
        # Arrange
        data = {"type": "unknown_type", "foo": "bar"}
        
        # Act
        cmd = parse_command(data)
        
        # Assert
        assert isinstance(cmd, Command)
```

### Criterios de Éxito

- [ ] 10+ Command subclasses implemented
- [ ] All commands serializable to dict
- [ ] `parse_command()` restores correct types
- [ ] Tests pass: `pytest tests/unit/core/test_commands.py -v`
- [ ] Type checking passes

### Referencias

- RASA CALM command architecture
- `archive/src/soni/core/commands.py` - Reference
