# Soni v2 - Milestone 6: Link/Call + Nested Flows

**Status**: Ready for Review  
**Date**: 2025-12-21  
**Type**: Design Document  
**Depends On**: M0, M1, M2, M3, M4, M5

---

## 1. Objective

Add flow composition:
- **Link**: Transition to another flow (no return)
- **Call**: Execute subflow and return

---

## 2. User Stories

### 2.1 Link (Transfer Control)

```yaml
# Main flow
steps:
  - say:
      step: intro
      message: "Welcome!"
  - link:
      step: go_menu
      target: main_menu  # Transfers control, no return
```

### 2.2 Call (Subflow with Return)

```yaml
# Main flow
steps:
  - collect:
      step: ask_action
      slot: action
      message: "What would you like to do?"
  - call:
      step: authenticate
      target: auth_flow  # Returns after auth_flow completes
  - say:
      step: continue
      message: "Authenticated! Continuing..."
```

---

## 3. Key Concepts

### 3.1 Flow Stack Behavior

| Pattern | Stack Operation | Return? |
|---------|-----------------|---------|
| **Link** | Pop current, push target | No |
| **Call** | Push target (keep current) | Yes |

### 3.2 Implementation via Commands

```python
# link_node
return {
    "commands": [
        {"type": "end_flow"},
        {"type": "start_flow", "flow_name": target}
    ]
}

# call_node
return {
    "commands": [{"type": "start_flow", "flow_name": target}]
}
```

### 3.3 Flow Completion Detection

When a flow reaches END and stack has parent:
- Pop current flow
- Resume parent flow at next step

```python
# In execute_node
if flow_completed and len(state["flow_stack"]) > 1:
    _, delta = flow_manager.pop_flow(state)
    # Parent flow resumes
```

---

## 4. Legacy Code Reference

### 4.1 FlowManager.pop_flow (REUSE)

**Source**: `archive/v1/src/soni/flow/manager.py`

```python
# Keep: Stack operations
# Keep: Cleanup of executed_steps
```

---

## 5. New Files

### 5.1 compiler/nodes/link.py

```python
"""LinkNodeFactory for M6."""

from typing import Any

from langgraph.runtime import Runtime

from soni.config.models import LinkStepConfig, StepConfig
from soni.core.types import DialogueState, NodeFunction, RuntimeContext
from soni.flow.manager import merge_delta


class LinkNodeFactory:
    """Factory for link step nodes (SRP: flow transfer only)."""

    def create(
        self,
        step: StepConfig,
        all_steps: list[StepConfig] | None = None,
        step_index: int | None = None,
    ) -> NodeFunction:
        """Create a link node function."""
        if not isinstance(step, LinkStepConfig):
            raise ValueError(f"LinkNodeFactory received wrong step type: {type(step).__name__}")
        
        target_flow = step.target
        
        async def link_node(
            state: DialogueState,
            runtime: Runtime[RuntimeContext],
        ) -> dict[str, Any]:
            """Link to another flow (no return)."""
            fm = runtime.context.flow_manager
            
            # Pop current flow
            _, pop_delta = fm.pop_flow(state)
            
            # Push target flow
            _, push_delta = fm.push_flow(state, target_flow)
            
            updates: dict[str, Any] = {}
            merge_delta(updates, pop_delta)
            merge_delta(updates, push_delta)
            
            return updates
        
        link_node.__name__ = f"link_{step.step}"
        return link_node


# Register: NodeFactoryRegistry.register("link", LinkNodeFactory())
```

### 5.2 compiler/nodes/call.py

```python
"""CallNodeFactory for M6."""

from typing import Any

from langgraph.runtime import Runtime

from soni.config.models import CallStepConfig, StepConfig
from soni.core.types import DialogueState, NodeFunction, RuntimeContext


class CallNodeFactory:
    """Factory for call step nodes (SRP: subflow invocation only)."""

    def create(
        self,
        step: StepConfig,
        all_steps: list[StepConfig] | None = None,
        step_index: int | None = None,
    ) -> NodeFunction:
        """Create a call node function."""
        if not isinstance(step, CallStepConfig):
            raise ValueError(f"CallNodeFactory received wrong step type: {type(step).__name__}")
        
        target_flow = step.target
        
        async def call_node(
            state: DialogueState,
            runtime: Runtime[RuntimeContext],
        ) -> dict[str, Any]:
            """Call a subflow (with return)."""
            fm = runtime.context.flow_manager
            
            # Push target flow (current stays on stack)
            _, delta = fm.push_flow(state, target_flow)
            
            return {
                "flow_stack": delta.flow_stack,
                "flow_slots": delta.flow_slots,
            }
        
        call_node.__name__ = f"call_{step.step}"
        return call_node


# Register: NodeFactoryRegistry.register("call", CallNodeFactory())
```

### 5.3 config/steps.py (Add)

```python
class LinkStepConfig(BaseStepConfig):
    type: Literal["link"] = "link"
    target: str = Field(description="Flow to link to")


class CallStepConfig(BaseStepConfig):
    type: Literal["call"] = "call"
    target: str = Field(description="Subflow to call")
```

### 5.4 dm/nodes/execute.py (Update)

```python
async def execute_node(state, runtime):
    # ... existing code ...
    
    # After subgraph completes:
    if not result.get("_need_input"):
        # Check if flow completed
        stack = result.get("flow_stack", [])
        
        # If multiple flows on stack and current finished, pop
        if len(stack) > 1:
            fm = runtime.context.flow_manager
            current_name = stack[-1]["flow_name"]
            
            # Check if subgraph reached END
            if _flow_completed(result, current_name):
                _, delta = fm.pop_flow(result)
                result = {**result, **delta.__dict__}
                # Loop to continue parent flow
                continue  # Re-invoke with parent flow
        
        return result
```

---

## 6. TDD Tests (AAA Format)

### 6.1 Integration Tests

```python
# tests/integration/test_m6_nested.py
@pytest.mark.asyncio
async def test_link_transfers_control():
    """Link step transfers to target flow without return."""
    # Arrange
    config = SoniConfig(flows={
        "main": FlowConfig(steps=[
            SayStepConfig(step="start", message="Starting..."),
            LinkStepConfig(step="go", target="other"),
            SayStepConfig(step="never", message="Never reached"),
        ]),
        "other": FlowConfig(steps=[
            SayStepConfig(step="end", message="In other flow!"),
        ]),
    })
    
    # Act
    async with RuntimeLoop(config) as runtime:
        response = await runtime.process_message("start")
    
    # Assert
    assert "In other flow!" in response
    assert "Never reached" not in response


@pytest.mark.asyncio
async def test_call_returns_to_parent():
    """Call step executes subflow then returns."""
    # Arrange
    config = SoniConfig(flows={
        "main": FlowConfig(steps=[
            SayStepConfig(step="before", message="Before call"),
            CallStepConfig(step="do_auth", target="auth"),
            SayStepConfig(step="after", message="After call"),
        ]),
        "auth": FlowConfig(steps=[
            SayStepConfig(step="auth_msg", message="Authenticating..."),
        ]),
    })
    
    # Act
    async with RuntimeLoop(config) as runtime:
        response = await runtime.process_message("start")
    
    # Assert
    assert "Authenticating" in response
    assert "After call" in response


@pytest.mark.asyncio
async def test_call_returns_to_parent():
    """Call step executes subflow then returns."""
    config = SoniConfig(flows={
        "main": FlowConfig(steps=[
            SayStepConfig(step="before", message="Before call"),
            CallStepConfig(step="do_auth", target="auth"),
            SayStepConfig(step="after", message="After call"),
        ]),
        "auth": FlowConfig(steps=[
            SayStepConfig(step="auth_msg", message="Authenticating..."),
        ]),
    })
    
    async with RuntimeLoop(config) as runtime:
        response = await runtime.process_message("start")
        assert "Authenticating" in response
        assert "After call" in response
```

---

## 7. Success Criteria

- [ ] Link transfers control to target flow
- [ ] Call pushes subflow and returns
- [ ] Parent flow resumes after call completes
- [ ] Flow stack correctly managed

---

## 8. Implementation Order

1. Write tests (RED)
2. Add `LinkStepConfig`, `CallStepConfig`
3. Create `compiler/nodes/link.py`
4. Create `compiler/nodes/call.py`
5. Update `execute_node` for flow completion
6. Run tests (GREEN)

---

## Next: M7 (Confirm + Patterns)
