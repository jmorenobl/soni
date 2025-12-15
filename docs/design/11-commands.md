# Soni Framework - Commands Specification

## Overview

Commands are the explicit contract between Dialogue Understanding (DU) and Dialogue Management (DM). The NLU produces Commands (pure data), and the CommandExecutor executes them deterministically via Handlers.

**Key Principle**: LLM interprets → Commands → DM executes deterministically.

## Command Types

### Base Command

```python
from pydantic import BaseModel, Field
from typing import Any

class Command(BaseModel):
    """Base class for all commands (pure data)."""
    pass
```

### Flow Control Commands

#### StartFlow

Start a new flow, optionally with pre-filled slots.

```python
class StartFlow(Command):
    """Start a new flow."""
    flow_name: str = Field(description="Name of flow to start")
    slots: dict[str, Any] = Field(
        default_factory=dict,
        description="Pre-filled slot values"
    )
```

**Examples**:
- `"I want to book a flight"` → `StartFlow(flow_name="book_flight")`
- `"Book from NYC to LA"` → `StartFlow(flow_name="book_flight", slots={"origin": "NYC", "destination": "LA"})`

#### CancelFlow

Cancel the current flow.

```python
class CancelFlow(Command):
    """Cancel current flow."""
    reason: str | None = Field(
        default=None,
        description="Reason for cancellation"
    )
```

**Examples**:
- `"Cancel"` → `CancelFlow()`
- `"Never mind"` → `CancelFlow(reason="user_changed_mind")`

---

### Slot Commands

#### SetSlot

Set a slot value in the current flow.

```python
class SetSlot(Command):
    """Set a slot value."""
    slot_name: str = Field(description="Name of slot to set")
    value: Any = Field(description="Value to set")
    confidence: float = Field(
        default=1.0,
        ge=0.0, le=1.0,
        description="Confidence in extraction"
    )
```

**Examples**:
- `"New York"` (when waiting for origin) → `SetSlot(slot_name="origin", value="New York")`
- `"Tomorrow"` → `SetSlot(slot_name="date", value="2024-12-16")`

#### CorrectSlot

Correct a previously set slot value.

```python
class CorrectSlot(Command):
    """Correct a previously set slot."""
    slot_name: str = Field(description="Name of slot to correct")
    new_value: Any = Field(description="New value")
```

**Examples**:
- `"Actually, Madrid not Barcelona"` → `CorrectSlot(slot_name="destination", new_value="Madrid")`
- `"I meant next Friday"` → `CorrectSlot(slot_name="date", new_value="2024-12-20")`

---

### Conversation Pattern Commands

#### Clarify

User asks for clarification without changing flow.

```python
class Clarify(Command):
    """User asks for clarification."""
    topic: str = Field(description="Topic of clarification")
```

**Examples**:
- `"What cities do you support?"` → `Clarify(topic="supported_cities")`
- `"Why do you need that?"` → `Clarify(topic="slot_purpose")`
- `"Help"` → `Clarify(topic="help")`

#### HumanHandoff

User requests human agent.

```python
class HumanHandoff(Command):
    """Request human agent."""
    reason: str | None = Field(
        default=None,
        description="Reason for handoff"
    )
```

**Examples**:
- `"Talk to a human"` → `HumanHandoff(reason="user_request")`
- `"I need real help"` → `HumanHandoff(reason="frustration")`

---

### Confirmation Commands

#### AffirmConfirmation

User confirms a pending action.

```python
class AffirmConfirmation(Command):
    """User confirms."""
    pass
```

**Examples**:
- `"Yes"` → `AffirmConfirmation()`
- `"That's correct"` → `AffirmConfirmation()`
- `"Proceed"` → `AffirmConfirmation()`

#### DenyConfirmation

User denies confirmation, optionally specifying what to change.

```python
class DenyConfirmation(Command):
    """User denies confirmation."""
    slot_to_change: str | None = Field(
        default=None,
        description="Specific slot to change, if mentioned"
    )
```

**Examples**:
- `"No"` → `DenyConfirmation()`
- `"No, change the date"` → `DenyConfirmation(slot_to_change="date")`
- `"Wait, the destination is wrong"` → `DenyConfirmation(slot_to_change="destination")`

---

## Command Handlers

Each command type has a corresponding handler. See [03-components.md](03-components.md) for full handler implementations.

| Command | Handler | Primary Action |
|---------|---------|----------------|
| `StartFlow` | `StartFlowHandler` | `flow_manager.push_flow()` |
| `CancelFlow` | `CancelFlowHandler` | `flow_manager.pop_flow()` |
| `SetSlot` | `SetSlotHandler` | `flow_manager.set_slot()` |
| `CorrectSlot` | `CorrectSlotHandler` | Validate + `set_slot()` |
| `Clarify` | `ClarifyHandler` | Generate explanation |
| `HumanHandoff` | `HumanHandoffHandler` | Trigger handoff action |
| `AffirmConfirmation` | `AffirmHandler` | Proceed to action |
| `DenyConfirmation` | `DenyHandler` | Return to slot collection |

---

## Multiple Commands

A single user message can produce multiple commands:

```python
# "Cancel this and check my balance"
commands = [
    CancelFlow(reason="user_request"),
    StartFlow(flow_name="check_balance")
]

# "Book a flight from NYC to LA tomorrow"
commands = [
    StartFlow(flow_name="book_flight"),
    SetSlot(slot_name="origin", value="NYC"),
    SetSlot(slot_name="destination", value="LA"),
    SetSlot(slot_name="date", value="2024-12-16")
]
```

Commands are executed **sequentially** by the CommandExecutor.

---

## Command Serialization

Commands are Pydantic models, automatically serializable:

```python
# Serialize for logging/storage
command = StartFlow(flow_name="book_flight", slots={"origin": "NYC"})
serialized = command.model_dump()
# {"flow_name": "book_flight", "slots": {"origin": "NYC"}}

# Deserialize
restored = StartFlow.model_validate(serialized)
```

---

## Handler Registry

```python
class CommandHandlerRegistry:
    """Maps command types to handlers."""

    _handlers: dict[type[Command], CommandHandler] = {
        StartFlow: StartFlowHandler(),
        CancelFlow: CancelFlowHandler(),
        SetSlot: SetSlotHandler(),
        CorrectSlot: CorrectSlotHandler(),
        Clarify: ClarifyHandler(),
        HumanHandoff: HumanHandoffHandler(),
        AffirmConfirmation: AffirmConfirmationHandler(),
        DenyConfirmation: DenyConfirmationHandler(),
    }

    def get(self, command_type: type[Command]) -> CommandHandler:
        return self._handlers[command_type]
```

**Adding New Commands (OCP)**:
1. Define new Command class (Pydantic model)
2. Create new Handler class implementing `CommandHandler` protocol
3. Register in `CommandHandlerRegistry`
4. No existing code modified

---

## Command Logging

All commands are logged for audit:

```python
# In CommandExecutor
async def execute(self, commands, state, context):
    for command in commands:
        # Execute
        handler = self.registry.get(type(command))
        result = await handler.execute(command, state, context)

        # Log for audit
        log_entry = {
            "command": type(command).__name__,
            "args": command.model_dump(),
            "timestamp": time.time(),
            "result": "success" if "error" not in result else "error"
        }
        state["command_log"].append(log_entry)
```

---

## Summary

| Aspect | Details |
|--------|---------|
| **Purpose** | Explicit contract between DU and DM |
| **Structure** | Pure Pydantic models (data only) |
| **Execution** | Deterministic via Handler Registry |
| **Extensibility** | OCP: new command = new handler + registry entry |
| **Serialization** | Automatic via Pydantic |
| **Audit** | Full command log in state |

---

**Design Version**: v2.0 (Command-Driven Architecture)
**Status**: Production-ready design specification
