# Soni v2 - Milestone 2: Collect + Interrupt

**Status**: Ready for Review  
**Date**: 2025-12-21  
**Type**: Design Document  
**Depends On**: M0, M1

---

## 1. Objective

Add slot collection with multi-turn conversation support via LangGraph interrupt.

---

## 2. User Story

```
Turn 1:
User: "hi"
Bot: "What is your name?"

Turn 2:
User: "Alice"
Bot: "Hello, Alice!"
```

---

## 3. Key Concepts

### 3.1 Interrupt Pattern (ADR-002)

**Critical Learning from LangGraph docs**: 
- `interrupt()` pauses execution and returns a value to the caller
- Resume via `Command(resume=value)` or re-invoking with checkpointer
- Node re-executes from the beginning on resume (use idempotency)
- Checkpointer is REQUIRED for interrupt to work

```python
# execute_node (orchestrator level)
while True:
    result = await subgraph.ainvoke(state)
    
    if not result["_need_input"]:
        return result
    
    # Interrupt HERE - returns prompt to caller
    resume_value = interrupt(result["_pending_prompt"])
    
    # On resume, inject user response as command
    state["commands"] = [{"type": "set_slot", "slot": prompt["slot"], "value": resume_value}]
```

### 3.2 Flag-Based Signaling

Subgraph nodes signal need for input via state flags, NOT by calling `interrupt()`:

```python
# collect_node returns flags
return {
    "_need_input": True,
    "_pending_prompt": {"slot": "name", "prompt": "What is your name?"}
}
```

---

## 4. Legacy Code Reference

### 4.1 FlowManager (REUSE fully)

**Source**: `archive/v1/src/soni/flow/manager.py`

```python
# Keep: FlowDelta pattern, immutable operations
class FlowManager:
    def push_flow(...) -> tuple[str, FlowDelta]: ...
    def set_slot(...) -> FlowDelta: ...
    def get_slot(...) -> Any: ...
```

### 4.2 CollectNodeFactory (ADAPT)

**Source**: `archive/v1/src/soni/compiler/nodes/collect.py`

```python
# Keep: Command consumption, slot check
# Remove: interrupt() call
# Add: _need_input flag return
```

### 4.3 Execute Node (ADAPT from ADR-002)

**Source**: `archive/v1/src/soni/dm/nodes/execute.py`

```python
# Keep: Two-phase interrupt pattern
# Simplify: Remove complex command handling for M2
```

---

## 5. New State Fields

```python
from soni.core.constants import FlowContextState

# Additional reducers for M2
def _merge_flow_slots(
    current: dict[str, dict[str, Any]],
    new: dict[str, dict[str, Any]],
) -> dict[str, dict[str, Any]]:
    """Reducer that deep-merges flow_slots dicts."""
    result = dict(current)
    for flow_id, slots in new.items():
        if flow_id in result:
            result[flow_id] = {**result[flow_id], **slots}
        else:
            result[flow_id] = slots
    return result


class FlowContext(TypedDict):
    """Context for a single flow instance on the stack."""
    flow_id: str  # Unique instance ID (UUID)
    flow_name: str
    flow_state: FlowContextState
    current_step: str | None
    step_index: int


class DialogueState(TypedDict):
    # From M1
    user_message: Annotated[str | None, _last_value_str]
    messages: Annotated[list[AnyMessage], add_messages]
    response: Annotated[str | None, _last_value_str]
    
    # NEW M2: Flow management
    flow_stack: list[FlowContext]
    flow_slots: Annotated[dict[str, dict[str, Any]], _merge_flow_slots]
    
    # NEW M2: Commands
    commands: Annotated[list[dict[str, Any]], _last_value_any]
    
    # NEW M2: Interrupt signaling
    _need_input: Annotated[bool, _last_value_any]
    _pending_prompt: Annotated[dict | None, _last_value_any]
```

---

## 6. New/Modified Files

### 6.1 core/types.py (Extended)

```python
# Add FlowContext, reducers, extended DialogueState
```

### 6.2 flow/manager.py (Copy from archive)

```python
# Full FlowManager with:
# - push_flow(), pop_flow()
# - set_slot(), get_slot()
# - FlowDelta returns
```

### 6.3 config/models.py (Add CollectStepConfig)

```python
class CollectStepConfig(BaseModel):
    step: str
    type: str = "collect"
    slot: str
    message: str
```

### 6.4 compiler/nodes/collect.py (New)

```python
"""CollectNodeFactory for M2."""

from typing import Any

from langgraph.runtime import Runtime

from soni.config.models import CollectStepConfig, StepConfig
from soni.core.types import DialogueState, NodeFunction, RuntimeContext
from soni.flow.manager import merge_delta


class CollectNodeFactory:
    """Factory for collect step nodes (SRP: slot collection only)."""

    def create(
        self,
        step: StepConfig,
        all_steps: list[StepConfig] | None = None,
        step_index: int | None = None,
    ) -> NodeFunction:
        """Create a collect node function."""
        if not isinstance(step, CollectStepConfig):
            raise ValueError(f"CollectNodeFactory received wrong step type: {type(step).__name__}")
        
        slot_name = step.slot
        prompt = step.message
        
        async def collect_node(
            state: DialogueState,
            runtime: Runtime[RuntimeContext],
        ) -> dict[str, Any]:
            """Collect slot value from user."""
            # ISP: Use SlotProvider interface
            fm = runtime.context.flow_manager
            
            # 1. Already filled?
            if fm.get_slot(state, slot_name):
                return {}
            
            # 2. Command provides value?
            for cmd in state.get("commands", []):
                if cmd.get("type") == "set_slot" and cmd.get("slot") == slot_name:
                    delta = fm.set_slot(state, slot_name, cmd["value"])
                    updates: dict[str, Any] = {"commands": []}  # Consume command
                    merge_delta(updates, delta)
                    return updates
            
            # 3. Need input
            return {
                "_need_input": True,
                "_pending_prompt": {"slot": slot_name, "prompt": prompt},
            }
        
        collect_node.__name__ = f"collect_{step.step}"
        return collect_node


# Register in factory.py:
# NodeFactoryRegistry.register("collect", CollectNodeFactory())
```

### 6.5 compiler/subgraph.py (Extend with router)

```python
def _create_router(valid_targets: set[str], default: str):
    """Create router that checks _need_input first."""
    def router(state):
        if state.get("_need_input"):
            return END
        return default
    return router
```

### 6.6 dm/nodes/execute.py (Interrupt loop)

```python
"""Execute node for M2 with interrupt loop."""

from typing import Any

from langgraph.runtime import Runtime
from langgraph.types import interrupt

from soni.core.types import DialogueState, RuntimeContext
from soni.flow.manager import merge_delta


async def execute_node(
    state: DialogueState,
    runtime: Runtime[RuntimeContext],
) -> dict[str, Any]:
    """Execute the active flow's subgraph with interrupt handling."""
    subgraph = runtime.context.subgraph
    flow_manager = runtime.context.flow_manager
    
    # Auto-push first flow if stack empty
    if not state.get("flow_stack"):
        _, delta = flow_manager.push_flow(state, "greet")
        # Apply delta to local state copy
        if delta.flow_stack:
            state = {**state, "flow_stack": delta.flow_stack}
        if delta.flow_slots:
            state = {**state, "flow_slots": delta.flow_slots}
    
    subgraph_state = dict(state)
    subgraph_state["_need_input"] = False
    
    while True:
        result = await subgraph.ainvoke(subgraph_state)
        
        if not result.get("_need_input"):
            return {"response": result.get("response")}
        
        # Interrupt and get user response
        prompt = result["_pending_prompt"]
        user_response = interrupt(prompt)
        
        # Inject as command for next iteration
        message = user_response if isinstance(user_response, str) else user_response.get("message", "")
        subgraph_state["commands"] = [{"type": "set_slot", "slot": prompt["slot"], "value": message}]
        subgraph_state.update(result)
```

### 6.7 runtime/loop.py (Add checkpointer)

```python
from langgraph.checkpoint.memory import MemorySaver

class RuntimeLoop:
    def __init__(self, config, checkpointer=None):
        self._checkpointer = checkpointer or MemorySaver()
    
    async def process_message(self, message: str, user_id: str = "default"):
        thread_id = f"thread_{user_id}"
        config = {"configurable": {"thread_id": thread_id, **context}}
        
        result = await self._graph.ainvoke(
            {"user_message": message},
            config
        )
        # Handle interrupt response
        ...
```

---

## 7. TDD Tests (AAA Format)

### 7.1 Integration Test

```python
# tests/integration/test_m2_collect.py
import pytest
from langgraph.checkpoint.memory import MemorySaver

from soni.config.models import SoniConfig, FlowConfig, CollectStepConfig, SayStepConfig
from soni.runtime.loop import RuntimeLoop


@pytest.mark.asyncio
async def test_collect_and_greet():
    """Two-turn conversation: collect name, then greet."""
    # Arrange
    config = SoniConfig(
        flows={
            "greet": FlowConfig(
                steps=[
                    CollectStepConfig(step="ask", slot="name", message="What is your name?"),
                    SayStepConfig(step="hello", message="Hello, {name}!"),
                ]
            )
        }
    )
    checkpointer = MemorySaver()
    
    # Act - Turn 1
    async with RuntimeLoop(config, checkpointer=checkpointer) as runtime:
        response1 = await runtime.process_message("hi", user_id="test")
    
    # Assert - Turn 1
    assert "What is your name?" in response1
    
    # Act - Turn 2
    async with RuntimeLoop(config, checkpointer=checkpointer) as runtime:
        response2 = await runtime.process_message("Alice", user_id="test")
    
    # Assert - Turn 2
    assert "Hello, Alice!" in response2


@pytest.mark.asyncio
async def test_collect_already_filled_skips():
    """If slot is already filled, collect node skips."""
    # Arrange - state with pre-filled slot
    ...
    
    # Act
    ...
    
    # Assert - returns {} (no action needed)
    ...
```

### 7.2 Unit Tests

```python
# tests/unit/compiler/test_collect_node.py
@pytest.mark.asyncio
async def test_collect_returns_need_input_when_empty():
    """Collect returns _need_input=True when slot is empty."""
    ...

@pytest.mark.asyncio
async def test_collect_uses_command_value():
    """Collect uses SetSlot command value."""
    ...

@pytest.mark.asyncio
async def test_collect_skips_when_slot_filled():
    """Collect returns {} when slot already has value."""
    ...
```

---

## 8. Success Criteria

- [ ] `test_collect_and_greet` passes (2-turn conversation)
- [ ] Interrupt works correctly
- [ ] State persists between turns (checkpointer)
- [ ] Commands are consumed after use

---

## 9. Implementation Order

1. Write integration test (RED)
2. Extend `core/types.py` with new fields
3. Copy `flow/manager.py` from archive
4. Add `CollectStepConfig`
5. Create `compiler/nodes/collect.py`
6. Update `compiler/subgraph.py` with router
7. Implement interrupt loop in `execute_node`
8. Update `runtime/loop.py` with checkpointer
9. Run tests (GREEN)

---

## Next: M3 (Set + Branch + While)
