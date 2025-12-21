# Soni v2 - Milestone 3: Set + Branch + While

**Status**: Ready for Review  
**Date**: 2025-12-21  
**Type**: Design Document  
**Depends On**: M0, M1, M2

---

## 1. Objective

Add conditional logic and slot manipulation:
- **Set**: Programmatic slot assignment
- **Branch**: Conditional routing based on slot values
- **While**: Loop constructs (transformed to branch + jump_to)

---

## 2. User Stories

### 2.1 Branch Flow

```yaml
steps:
  - collect:
      step: ask_amount
      slot: amount
      message: "How much to transfer?"
  - branch:
      step: check_auth
      slot: amount
      cases:
        ">1000": extra_auth
        default: proceed
  - say:
      step: extra_auth
      message: "Large transfer - extra auth needed"
  - say:
      step: proceed
      message: "Processing transfer..."
```

### 2.2 Set Step

```yaml
steps:
  - set:
      step: init
      slots:
        greeting: "Hello, {name}!"
        timestamp: "now()"
```

---

## 3. Key Concepts

### 3.1 Idempotency via `_executed_steps`

**Problem**: When subgraph is re-invoked after interrupt, side-effect nodes (say, action) re-execute.

**Solution**: Track executed steps per flow:

```python
executed = state["_executed_steps"].get(flow_id, set())
if step_id in executed:
    return {}  # Skip

# ... execute ...

return {"_executed_steps": {flow_id: {step_id}}}
```

### 3.2 Branch Routing

Branch node sets `_branch_target` which router reads:

```python
# branch_node
return {"_branch_target": target_step}

# router
if state.get("_branch_target"):
    return state["_branch_target"]
```

### 3.3 While Loop Transformation

While loops are compiled to branch + jump_to pattern:

```python
# while condition: do [step1, step2] exit_to next
# Becomes:
# - branch: check condition -> (true: step1, false: next)
# - step1 + step2 with jump_to back to branch
```

---

## 4. Legacy Code Reference

### 4.1 BranchNodeFactory (ADAPT)

**Source**: `archive/v1/src/soni/compiler/nodes/branch.py`

```python
# Keep: Expression evaluation, case matching
# Keep: _branch_target pattern
```

### 4.2 SetNodeFactory (ADAPT)

**Source**: `archive/v1/src/soni/compiler/nodes/set.py`

```python
# Keep: Template substitution
# Keep: Condition evaluation
```

### 4.3 WhileStepConfig (ADAPT)

**Source**: `archive/v1/src/soni/config/steps.py`

```python
# Keep: Transformation to branch + jump_to
```

---

## 5. New State Fields

```python
class DialogueState(TypedDict):
    # From M1, M2
    ...
    
    # NEW M3: Idempotency
    _executed_steps: Annotated[dict[str, set[str]], _merge_dicts]
    
    # NEW M3: Branch routing
    _branch_target: Annotated[str | None, _last_value]
```

---

## 6. New Files

### 6.1 compiler/nodes/set.py

```python
"""SetNodeFactory for M3."""

from typing import Any

from langgraph.runtime import Runtime

from soni.config.models import SetStepConfig, StepConfig
from soni.core.expression import evaluate_expression, evaluate_value
from soni.core.types import DialogueState, NodeFunction, RuntimeContext
from soni.flow.manager import merge_delta


class SetNodeFactory:
    """Factory for set step nodes (SRP: slot assignment only)."""

    def create(
        self,
        step: StepConfig,
        all_steps: list[StepConfig] | None = None,
        step_index: int | None = None,
    ) -> NodeFunction:
        """Create a set node function."""
        if not isinstance(step, SetStepConfig):
            raise ValueError(f"SetNodeFactory received wrong step type: {type(step).__name__}")
        
        slots_config = step.slots
        condition = step.condition
        
        async def set_node(
            state: DialogueState,
            runtime: Runtime[RuntimeContext],
        ) -> dict[str, Any]:
            """Set slot values programmatically."""
            fm = runtime.context.flow_manager
            
            # Optional condition
            if condition:
                result = evaluate_expression(condition, fm.get_all_slots(state))
                if not result:
                    return {}
            
            updates: dict[str, Any] = {}
            for slot_name, value_expr in slots_config.items():
                value = evaluate_value(value_expr, fm.get_all_slots(state))
                delta = fm.set_slot(state, slot_name, value)
                merge_delta(updates, delta)
            
            return updates
        
        set_node.__name__ = f"set_{step.step}"
        return set_node


# Register: NodeFactoryRegistry.register("set", SetNodeFactory())
```

### 6.2 compiler/nodes/branch.py

```python
"""BranchNodeFactory for M3."""

from typing import Any

from langgraph.runtime import Runtime

from soni.config.models import BranchStepConfig, StepConfig
from soni.core.expression import evaluate_expression, matches
from soni.core.types import DialogueState, NodeFunction, RuntimeContext


class BranchNodeFactory:
    """Factory for branch step nodes (SRP: routing only)."""

    def create(
        self,
        step: StepConfig,
        all_steps: list[StepConfig] | None = None,
        step_index: int | None = None,
    ) -> NodeFunction:
        """Create a branch node function."""
        if not isinstance(step, BranchStepConfig):
            raise ValueError(f"BranchNodeFactory received wrong step type: {type(step).__name__}")
        
        slot_name = step.slot
        expression = step.evaluate
        cases = step.cases
        
        async def branch_node(
            state: DialogueState,
            runtime: Runtime[RuntimeContext],
        ) -> dict[str, Any]:
            """Route based on slot value or expression."""
            fm = runtime.context.flow_manager
            
            if expression:
                value = evaluate_expression(expression, fm.get_all_slots(state))
            else:
                value = fm.get_slot(state, slot_name)
            
            target = cases.get("default")
            for case_value, case_target in cases.items():
                if case_value == "default":
                    continue
                if matches(value, case_value):
                    target = case_target
                    break
            
            return {"_branch_target": target}
        
        branch_node.__name__ = f"branch_{step.step}"
        return branch_node


# Register: NodeFactoryRegistry.register("branch", BranchNodeFactory())
```

### 6.3 core/expression.py

```python
def evaluate_expression(expr: str, slots: dict) -> Any:
    """Safely evaluate expression with slot context."""
    # Support: comparisons, arithmetic, simple functions
    ...

def evaluate_value(value_expr: str | Any, slots: dict) -> Any:
    """Evaluate value expression with template substitution."""
    if isinstance(value_expr, str) and "{" in value_expr:
        return value_expr.format(**slots)
    return value_expr
```

### 6.4 Update compiler/subgraph.py

```python
def _create_router(step_names: list[str], default: str):
    def router(state):
        # Priority 1: Need input
        if state.get("_need_input"):
            return END
        
        # Priority 2: Branch target
        target = state.get("_branch_target")
        if target and target in step_names:
            return target
        
        # Default: next step
        return default
    
    return router
```

---

## 7. TDD Tests (AAA Format)

### 7.1 Integration Tests

```python
# tests/integration/test_m3_branch.py
@pytest.mark.asyncio
async def test_branch_routes_based_on_value():
    """Branch routes to correct step based on slot value."""
    # Arrange
    config = SoniConfig(flows={"test": FlowConfig(steps=[
        SetStepConfig(step="init", slots={"amount": 500}),
        BranchStepConfig(
            step="check",
            slot="amount",
            cases={">1000": "large", "default": "small"}
        ),
        SayStepConfig(step="large", message="Large amount"),
        SayStepConfig(step="small", message="Small amount"),
    ])})
    
    # Act
    async with RuntimeLoop(config) as runtime:
        response = await runtime.process_message("start")
    
    # Assert
    assert "Small amount" in response
```

### 7.2 Unit Tests

```python
# tests/unit/compiler/test_branch_node.py
@pytest.mark.asyncio
async def test_branch_returns_target():
    """Branch returns _branch_target based on slot value."""
    ...

# tests/unit/compiler/test_set_node.py
@pytest.mark.asyncio
async def test_set_assigns_literal_value():
    """Set assigns literal values to slots."""
    ...

@pytest.mark.asyncio
async def test_set_substitutes_templates():
    """Set substitutes {slot} templates."""
    ...
```

---

## 8. Success Criteria

- [ ] Branch routing works
- [ ] Set node assigns values
- [ ] Idempotency prevents re-execution
- [ ] While loops transform correctly (optional for M3)

---

## 9. Implementation Order

1. Write tests (RED)
2. Add `_executed_steps`, `_branch_target` to state
3. Create `core/expression.py`
4. Create `compiler/nodes/set.py`
5. Create `compiler/nodes/branch.py`
6. Update `compiler/subgraph.py` router
7. Add idempotency to `say_node`
8. Run tests (GREEN)

---

## Next: M4 (CommandGenerator - NLU)
