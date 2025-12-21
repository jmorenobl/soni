# Soni v2 - Milestone 5: Action + Validation

**Status**: Ready for Review  
**Date**: 2025-12-21  
**Type**: Design Document  
**Depends On**: M0, M1, M2, M3, M4

---

## 1. Objective

Add action execution and slot validation:
- **Action**: Call external APIs/functions
- **Validation**: Validate slot values before proceeding

---

## 2. User Stories

### 2.1 Action Step

```yaml
steps:
  - action:
      step: fetch_balance
      call: get_account_balance
      map_outputs:
        balance: account_balance
  - say:
      step: show
      message: "Your balance is ${account_balance}"
```

### 2.2 Slot Validation

```yaml
slots:
  amount:
    type: float
    validator: validate_positive_amount
    validation_error_message: "Amount must be positive"

steps:
  - collect:
      step: ask_amount
      slot: amount
      message: "How much?"
```

---

## 3. Key Concepts

### 3.1 Action Registry

```python
class ActionRegistry:
    def register(self, name: str, handler: Callable): ...
    async def execute(self, name: str, slots: dict) -> dict: ...
```

### 3.2 Output Mapping

Actions return dicts, mapped to slots via `map_outputs`:

```python
# Action returns: {"balance": 1234.56, "currency": "USD"}
# map_outputs: {"balance": "account_balance"}
# Result: slot "account_balance" = 1234.56
```

### 3.3 Validation Pattern

```python
async def collect_node(state, runtime):
    # After getting value...
    if validator:
        is_valid = await validate(value, validator)
        if not is_valid:
            return {
                "_need_input": True,
                "_pending_prompt": {"error": validation_error_message, ...}
            }
    
    # Valid - set slot
    ...
```

---

## 4. Legacy Code Reference

### 4.1 ActionRegistry (ADAPT)

**Source**: `archive/v1/src/soni/actions/registry.py`

```python
# Keep: Registration pattern
# Keep: Slot context passing
```

### 4.2 ActionNodeFactory (ADAPT)

**Source**: `archive/v1/src/soni/compiler/nodes/action.py`

```python
# Keep: Output mapping
# Keep: Idempotency check
```

---

## 5. New Files

### 5.1 actions/registry.py

```python
"""Action registry for custom handlers."""

from typing import Any, Callable, Awaitable

ActionHandler = Callable[[dict[str, Any]], Awaitable[dict[str, Any]]]


class ActionRegistry:
    def __init__(self):
        self._handlers: dict[str, ActionHandler] = {}
    
    def register(self, name: str, handler: ActionHandler) -> None:
        """Register an action handler."""
        self._handlers[name] = handler
    
    async def execute(self, name: str, slots: dict[str, Any]) -> dict[str, Any]:
        """Execute action with current slots."""
        if name not in self._handlers:
            raise ValueError(f"Unknown action: {name}")
        return await self._handlers[name](slots)
    
    def __contains__(self, name: str) -> bool:
        return name in self._handlers
```

### 5.2 compiler/nodes/action.py

```python
"""ActionNodeFactory for M5."""

from typing import Any

from langgraph.runtime import Runtime

from soni.actions.registry import ActionRegistry
from soni.config.models import ActionStepConfig, StepConfig
from soni.core.types import DialogueState, NodeFunction, RuntimeContext
from soni.flow.manager import merge_delta


class ActionNodeFactory:
    """Factory for action step nodes (SRP: action execution only)."""

    def create(
        self,
        step: StepConfig,
        all_steps: list[StepConfig] | None = None,
        step_index: int | None = None,
    ) -> NodeFunction:
        """Create an action node function."""
        if not isinstance(step, ActionStepConfig):
            raise ValueError(f"ActionNodeFactory received wrong step type: {type(step).__name__}")
        
        action_name = step.call
        output_mapping = step.map_outputs or {}
        
        async def action_node(
            state: DialogueState,
            runtime: Runtime[RuntimeContext],
        ) -> dict[str, Any]:
            """Execute action and map outputs to slots."""
            fm = runtime.context.flow_manager
            flow_id = fm.get_active_flow_id(state)
            
            # IDEMPOTENCY
            if flow_id and step_index is not None:
                step_id = f"step_{step_index}"
                executed = state.get("_executed_steps", {}).get(flow_id, set())
                if step_id in executed:
                    return {}
            
            # Get current slots
            slots = fm.get_all_slots(state)
            
            # Execute action
            action_registry: ActionRegistry = runtime.context.action_registry
            result = await action_registry.execute(action_name, slots)
            
            # Map outputs to slots
            updates: dict[str, Any] = {}
            for action_key, slot_name in output_mapping.items():
                if action_key in result:
                    delta = fm.set_slot(state, slot_name, result[action_key])
                    merge_delta(updates, delta)
            
            # Mark executed
            if flow_id and step_index is not None:
                updates["_executed_steps"] = {flow_id: {f"step_{step_index}"}}
            
            return updates
        
        action_node.__name__ = f"action_{step.step}"
        return action_node


# Register: NodeFactoryRegistry.register("action", ActionNodeFactory())
```

### 5.3 core/validation.py

```python
"""Slot validation helpers."""

ValidatorFn = Callable[[Any, dict[str, Any]], bool | Awaitable[bool]]

_validators: dict[str, ValidatorFn] = {}


def register_validator(name: str, fn: ValidatorFn):
    """Register a validator function."""
    _validators[name] = fn


async def validate(value: Any, validator_name: str, slots: dict) -> bool:
    """Run validator on value."""
    if validator_name not in _validators:
        return True  # No validator = valid
    
    result = _validators[validator_name](value, slots)
    if hasattr(result, "__await__"):
        return await result
    return result
```

---

## 6. TDD Tests (AAA Format)

### 6.1 Integration Test

```python
# tests/integration/test_m5_action.py
@pytest.mark.asyncio
async def test_action_maps_outputs():
    """Action executes and maps outputs to slots."""
    # Arrange
    async def mock_balance(slots):
        return {"balance": 1234.56}
    
    registry = ActionRegistry()
    registry.register("get_balance", mock_balance)
    
    config = SoniConfig(flows={"test": FlowConfig(steps=[
        ActionStepConfig(
            step="fetch",
            call="get_balance",
            map_outputs={"balance": "account_balance"}
        ),
        SayStepConfig(step="show", message="Balance: ${account_balance}"),
    ])})
    
    # Act
    async with RuntimeLoop(config, action_registry=registry) as runtime:
        response = await runtime.process_message("check balance")
    
    # Assert
    assert "1234.56" in response
```

### 6.2 Unit Tests

```python
# tests/unit/actions/test_registry.py
@pytest.mark.asyncio
async def test_registry_executes_handler():
    """Registry executes registered handler."""
    ...

# tests/unit/compiler/test_action_node.py
@pytest.mark.asyncio
async def test_action_node_is_idempotent():
    """Action node skips if already executed."""
    ...
```

---

## 7. Success Criteria

- [ ] Actions execute and return results
- [ ] Output mapping works
- [ ] Actions are idempotent
- [ ] Validation rejects invalid values (optional for M5)

---

## 8. Implementation Order

1. Write tests (RED)
2. Create `actions/registry.py`
3. Create `compiler/nodes/action.py`
4. Create `core/validation.py`
5. Update `collect_node` for validation
6. Run tests (GREEN)

---

## Next: M6 (Link/Call + Nested Flows)
