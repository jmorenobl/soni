# Soni v2 - Milestone 7: Confirm + Patterns

**Status**: Ready for Review
**Date**: 2025-12-21
**Type**: Design Document
**Depends On**: M0, M1, M2, M3, M4, M5, M6

---

## 1. Objective

Add confirmation dialogs and conversation patterns:
- **Confirm**: Validate with user before proceeding
- **Patterns**: Handle corrections, cancellations, digressions

---

## 2. User Stories

### 2.1 Confirmation

```
Bot: "Transfer $100 to savings. Confirm?"
User: "Actually make it $50"  ← Correction
Bot: "Transfer $50 to savings. Confirm?"
User: "Yes"
Bot: "Done!"
```

### 2.2 Cancellation

```
Bot: "What's your account number?"
User: "cancel"  ← Cancellation
Bot: "No problem. Is there anything else I can help with?"
```

### 2.3 Digression

```
Bot: "How much to transfer?"
User: "What's my balance first?"  ← Digression
Bot: "Your balance is $1,234.56"
Bot: "Back to transfer - how much?"  ← Resume
```

---

## 3. Key Concepts

### 3.1 System Patterns (CALM-style)

| Pattern | Trigger | Action |
|---------|---------|--------|
| **Correction** | "no, I meant X" | Update slot, continue |
| **Cancellation** | "cancel", "stop" | Pop flow, confirm exit |
| **Clarification** | "what?", "explain" | Re-explain, continue |
| **ChitChat** | Off-topic | Respond, stay in flow |
| **Handoff** | "speak to human" | Escalate |

### 3.2 Pattern Detection (NLU Commands)

```python
# SoniDU detects patterns as commands:
class Correction(BaseModel):
    type: str = "correction"
    slot: str
    new_value: Any

class Cancellation(BaseModel):
    type: str = "cancel_flow"
```

### 3.3 Confirm Node Flow

```
confirm_node:
  1. Check if confirmation slot set
  2. If affirmed → continue
  3. If denied with correction → update slot, re-prompt
  4. If denied without → jump to on_deny target
  5. Else → prompt for confirmation
```

---

## 4. Legacy Code Reference

### 4.1 ConfirmNodeFactory (ADAPT)

**Source**: `archive/v1/src/soni/compiler/nodes/confirm.py`

```python
# Keep: State machine logic
# Simplify: Remove interrupt-based handlers
# Keep: Retry logic
```

### 4.2 Pattern Handlers (ADAPT)

**Source**: `archive/v1/src/soni/dm/patterns/`

```python
# Keep: Handler interface
# Keep: ChitChat, Correction patterns
```

---

## 5. New Files

### 5.1 core/commands.py (Extend)

```python
class AffirmConfirmation(BaseModel):
    type: str = "affirm"

class DenyConfirmation(BaseModel):
    type: str = "deny"

class Correction(BaseModel):
    type: str = "correction"
    slot: str
    new_value: Any
```

### 5.2 compiler/nodes/confirm.py

```python
"""ConfirmNodeFactory for M7."""

from typing import Any

from langgraph.runtime import Runtime

from soni.config.models import ConfirmStepConfig, StepConfig
from soni.core.types import DialogueState, NodeFunction, RuntimeContext


class ConfirmNodeFactory:
    """Factory for confirm step nodes (SRP: confirmation handling only)."""

    def create(
        self,
        step: StepConfig,
        all_steps: list[StepConfig] | None = None,
        step_index: int | None = None,
    ) -> NodeFunction:
        """Create a confirm node function."""
        if not isinstance(step, ConfirmStepConfig):
            raise ValueError(f"ConfirmNodeFactory received wrong step type: {type(step).__name__}")

        slot_name = step.slot
        prompt = step.message or f"Please confirm {slot_name}"
        on_confirm = step.on_confirm
        on_deny = step.on_deny

        async def confirm_node(
            state: DialogueState,
            runtime: Runtime[RuntimeContext],
        ) -> dict[str, Any]:
            """Confirm slot value with user."""
            fm = runtime.context.flow_manager

            # Check for confirmation response
            for cmd in state.get("commands", []):
                if cmd.get("type") == "affirm":
                    return {"commands": [], "_branch_target": on_confirm}

                if cmd.get("type") == "deny":
                    return {"commands": [], "_branch_target": on_deny}

                if cmd.get("type") == "correction":
                    delta = fm.set_slot(state, cmd["slot"], cmd["new_value"])
                    return {
                        "flow_slots": delta.flow_slots if delta else {},
                        "commands": [],
                    }

            # Need confirmation
            slot_value = fm.get_slot(state, slot_name)
            formatted_prompt = prompt.format(**{slot_name: slot_value}) if slot_value else prompt

            return {
                "_need_input": True,
                "_pending_prompt": {
                    "type": "confirm",
                    "slot": slot_name,
                    "value": slot_value,
                    "prompt": formatted_prompt,
                },
            }

        confirm_node.__name__ = f"confirm_{step.step}"
        return confirm_node


# Register: NodeFactoryRegistry.register("confirm", ConfirmNodeFactory())
```

### 5.3 dm/patterns/base.py

```python
"""Base pattern handler interface."""

from abc import ABC, abstractmethod
from typing import Any


class PatternHandler(ABC):
    @abstractmethod
    async def can_handle(self, command: dict, state: dict) -> bool:
        """Check if this handler can process the command."""
        ...

    @abstractmethod
    async def handle(self, command: dict, state: dict, context: Any) -> dict:
        """Handle the pattern and return state updates."""
        ...
```

### 5.4 dm/patterns/cancellation.py

```python
class CancellationHandler(PatternHandler):
    async def can_handle(self, command, state):
        return command.get("type") == "cancel_flow"

    async def handle(self, command, state, context):
        fm = context.flow_manager

        # Pop current flow
        _, delta = fm.pop_flow(state)

        return {
            "flow_stack": delta.flow_stack,
            "_executed_steps": delta.executed_steps,
            "response": "No problem. Is there anything else I can help with?",
        }
```

### 5.5 dm/patterns/correction.py

```python
class CorrectionHandler(PatternHandler):
    async def can_handle(self, command, state):
        return command.get("type") == "correction"

    async def handle(self, command, state, context):
        fm = context.flow_manager

        delta = fm.set_slot(state, command["slot"], command["new_value"])

        return {"flow_slots": delta.flow_slots}
```

### 5.6 dm/patterns/digression.py

```python
class DigressionHandler(PatternHandler):
    """Handle off-flow intents that should pause, not replace, current flow."""

    async def can_handle(self, command, state):
        # StartFlow for a different flow while in active flow
        return (
            command.get("type") == "start_flow" and
            len(state.get("flow_stack", [])) > 0
        )

    async def handle(self, command, state, context):
        fm = context.flow_manager

        # Push new flow (digression)
        _, delta = fm.push_flow(state, command["flow_name"])

        return {
            "flow_stack": delta.flow_stack,
            "flow_slots": delta.flow_slots,
            "_digression_pending": True,
        }
```

---

## 6. TDD Tests (AAA Format)

### 6.1 Integration Tests

```python
# tests/integration/test_m7_confirm.py
@pytest.mark.asyncio
async def test_confirm_affirm_continues():
    """User affirms confirmation and flow continues."""
    # Arrange
    ...

    # Act
    ...

    # Assert
    ...

@pytest.mark.asyncio
async def test_confirm_deny_routes_to_on_deny():
    """User denies and flow routes to on_deny."""
    # Arrange
    ...

    # Act
    ...

    # Assert
    ...

@pytest.mark.asyncio
async def test_confirm_correction_updates_slot():
    """User corrects value during confirmation."""
    # Arrange
    config = SoniConfig(flows={"transfer": FlowConfig(steps=[
        CollectStepConfig(step="get_amount", slot="amount", message="How much?"),
        ConfirmStepConfig(step="confirm", slot="amount", message="Transfer ${amount}?"),
        SayStepConfig(step="done", message="Transferred ${amount}"),
    ])})
    checkpointer = MemorySaver()

    # Act & Assert - Turn 1: Start
    async with RuntimeLoop(config, checkpointer=checkpointer) as runtime:
        response1 = await runtime.process_message("transfer", user_id="u1")

    # Act & Assert - Turn 2: Provide amount
    async with RuntimeLoop(config, checkpointer=checkpointer) as runtime:
        response2 = await runtime.process_message("100", user_id="u1")
    assert "Transfer $100?" in response2

    # Act & Assert - Turn 3: Correction
    async with RuntimeLoop(config, checkpointer=checkpointer) as runtime:
        response3 = await runtime.process_message("actually 50", user_id="u1")
    assert "Transfer $50?" in response3

    # Act & Assert - Turn 4: Confirm
    async with RuntimeLoop(config, checkpointer=checkpointer) as runtime:
        response4 = await runtime.process_message("yes", user_id="u1")
    assert "Transferred $50" in response4
```

---

## 7. Success Criteria

- [ ] Confirm → Affirm works
- [ ] Confirm → Deny routes correctly
- [ ] Correction updates slot and re-prompts
- [ ] Cancellation pops flow
- [ ] Digression pushes and returns

---

## 8. Implementation Order

1. Write tests (RED)
2. Add confirmation commands to NLU
3. Create `compiler/nodes/confirm.py`
4. Create pattern handlers
5. Update `execute_node` to process patterns
6. Run tests (GREEN)

---

## Next: M8 (Response Rephraser)
