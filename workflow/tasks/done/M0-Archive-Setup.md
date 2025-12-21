# Soni v2 - Milestone 0: Archive & Fresh Start

**Status**: Ready for Review
**Date**: 2025-12-21
**Type**: Design Document

---

## 1. Objective

Archive current `src/soni` and `tests/` code, then set up a fresh incremental structure while preserving:
- Best practices already established
- Core type definitions that work well
- Test infrastructure patterns
- **CLI and Server modules** (keep active, adapt as needed)

---

## 2. Best Practices to Preserve

### 2.1 TypedDict + Reducers Pattern

**Location**: `src/soni/core/types.py`

```python
# EXCELLENT: Reducers for LangGraph state management
def _last_value_any(current: Any, new: Any) -> Any:
    """Generic reducer that always returns the new value."""
    return new

def _merge_flow_slots(
    current: dict[str, dict[str, Any]],
    new: dict[str, dict[str, Any]],
) -> dict[str, dict[str, Any]]:
    """Deep-merges flow_slots dicts."""
    result = dict(current)
    for flow_id, slots in new.items():
        if flow_id in result:
            result[flow_id] = {**result[flow_id], **slots}
        else:
            result[flow_id] = slots
    return result
```

**Keep**: This pattern is essential for LangGraph state management.

### 2.2 FlowDelta Immutability Pattern

**Location**: `src/soni/core/types.py`

```python
@dataclass
class FlowDelta:
    """State delta returned by FlowManager mutation methods."""
    flow_stack: list[FlowContext] | None = None
    flow_slots: dict[str, dict[str, Any]] | None = None
    executed_steps: dict[str, set[str]] | None = None
```

**Keep**: Immutable mutations via deltas is a critical pattern.

### 2.3 Protocol-based DI

**Location**: `src/soni/core/types.py`

```python
@runtime_checkable
class FlowManagerProtocol(Protocol):
    """Protocol for flow stack operations."""
    def push_flow(self, state: DialogueState, flow_name: str) -> FlowDelta: ...
    def pop_flow(self, state: DialogueState) -> tuple[FlowContext | None, FlowDelta]: ...
```

**Keep**: Interface Segregation Principle for testability.

### 2.4 Test Structure

**Location**: `tests/`

```
tests/
├── conftest.py          # Shared fixtures
├── factories.py         # Test object factories
├── unit/                # Module-level tests
│   ├── core/
│   ├── compiler/
│   ├── dm/
│   └── ...
├── integration/         # Cross-module tests
└── e2e/                 # End-to-end tests
```

**Keep**: This structure with `conftest.py`, `factories.py`, unit/integration split.

### 2.5 Factory Pattern for Tests

**Location**: `tests/factories.py`

```python
def make_dialogue_state(**overrides: Any) -> dict:
    """Create a DialogueState with defaults, allowing overrides."""
    defaults = {
        "messages": [],
        "flow_stack": [],
        "flow_slots": {},
        "turn_count": 0,
        "user_message": None,
    }
    return {**defaults, **overrides}
```

**Keep**: Clean test factories.

---

## 3. What to Archive vs Rewrite

### 3.1 Archive (to `archive/v1_2025_12_21/`)

| Directory | Reason |
|-----------|--------|
| `src/soni/actions/` | Rewrite with cleaner interface |
| `src/soni/compiler/` | Edge routing issues |
| `src/soni/core/` | Keep types.py, rewrite rest |
| `src/soni/dm/` | Complex, has bugs |
| `src/soni/du/` | Keep base.py patterns |
| `src/soni/flow/` | Rewrite manager |
| `src/soni/runtime/` | Overloaded |
| `src/soni/dataset/` | Keep for M9 reference |
| `tests/` | Full backup for reference |

### 3.2 Keep Active (NOT archived)

> [!IMPORTANT]
> These modules stay in `src/soni/` and adapt incrementally.

| Directory | Reason | Interface Contract |
|-----------|--------|--------------------|
| `src/soni/cli/` | Works as-is | Depends only on `RuntimeLoop` |
| `src/soni/server/` | Works as-is | Depends only on `RuntimeLoop` |

**Interface Contract** (RuntimeLoop must provide):
```python
class RuntimeLoop:
    async def __aenter__(self) -> "RuntimeLoop": ...
    async def __aexit__(self, *args) -> None: ...
    async def process_message(self, message: str, user_id: str = "default") -> str: ...
    async def get_state(self, user_id: str) -> DialogueState | None: ...
    async def reset_state(self, user_id: str) -> None: ...
```

---

## 4. Fresh Structure for M1

```
src/soni/
├── __init__.py
├── core/
│   ├── __init__.py
│   ├── types.py          # DialogueState (minimal), reducers
│   └── state.py          # create_empty_state()
├── config/
│   ├── __init__.py
│   └── models.py         # SoniConfig, FlowConfig, SayStepConfig
├── compiler/
│   ├── __init__.py
│   ├── subgraph.py       # build_flow_subgraph()
│   └── nodes/
│       ├── __init__.py
│       └── say.py        # SayNodeFactory
├── dm/
│   ├── __init__.py
│   ├── builder.py        # build_orchestrator()
│   └── nodes/
│       ├── __init__.py
│       └── execute.py    # execute_node (simple for M1)
└── runtime/
    ├── __init__.py
    └── loop.py           # RuntimeLoop (minimal)
```

---

## 5. M1 Minimal DialogueState

For M1 (Hello World), we need only:

```python
class DialogueState(TypedDict):
    """Minimal state for M1: Hello World."""
    user_message: Annotated[str | None, _last_value_str]
    messages: Annotated[list[AnyMessage], add_messages]
    response: Annotated[str | None, _last_value_any]
```

**Incremental additions per milestone:**

| Milestone | New Fields |
|-----------|------------|
| M1 | user_message, messages, response |
| M2 | flow_stack, flow_slots, commands, _need_input, _pending_prompt |
| M3 | _executed_steps, _branch_target |
| M4 | (uses existing) |
| M5 | action_result |
| M6 | (uses existing) |
| M7 | waiting_for_slot, waiting_for_slot_type |

---

## 6. Execution Plan

### Step 1: Archive (Selective - Exclude CLI/Server)

```bash
mkdir -p archive/v1_2025_12_21

# Archive modules to rewrite
for dir in actions compiler core dm du flow runtime dataset; do
    cp -r src/soni/$dir archive/v1_2025_12_21/$dir 2>/dev/null || true
done

# Archive tests
cp -r tests archive/v1_2025_12_21/tests

# CLI and Server stay in src/soni/ - NOT archived
```

### Step 2: Clear Archived Modules (Keep cli/, server/)

```bash
# Remove only archived modules, keep cli/ and server/
for dir in actions compiler core dm du flow runtime dataset; do
    rm -rf src/soni/$dir
done

# Recreate directory structure
mkdir -p src/soni/{core,config,compiler/nodes,dm/nodes,runtime,flow}
for d in src/soni/{core,config,compiler,dm,runtime,flow,compiler/nodes,dm/nodes}; do
    touch $d/__init__.py
done
```

### Step 5: Verify Import Works

```bash
uv run python -c "import soni; print('OK')"
```

---

## 7. TDD Approach for M1

### First Test (RED)

```python
# tests/integration/test_m1_hello_world.py
import pytest
from soni.config.models import SoniConfig, FlowConfig, SayStepConfig
from soni.runtime.loop import RuntimeLoop

@pytest.mark.asyncio
async def test_hello_world():
    """M1: A flow with a single say step returns the message."""
    config = SoniConfig(flows={
        "greet": FlowConfig(steps=[
            SayStepConfig(step="hello", message="Hello, World!")
        ])
    })

    async with RuntimeLoop(config) as runtime:
        response = await runtime.process_message("hi")
        assert response == "Hello, World!"
```

### Implementation Order

1. **config/models.py** - Pydantic models
2. **core/types.py** - Minimal DialogueState
3. **core/state.py** - create_empty_state()
4. **compiler/nodes/say.py** - SayNodeFactory
5. **compiler/subgraph.py** - build_flow_subgraph()
6. **dm/nodes/execute.py** - execute_node
7. **dm/builder.py** - build_orchestrator()
8. **runtime/loop.py** - RuntimeLoop

---

## 8. Success Criteria

- [ ] `archive/v1_2025_12_21/` contains full backup
- [ ] Fresh `src/soni/` structure created
- [ ] `uv run python -c "import soni"` works
- [ ] Test infrastructure preserved (`conftest.py`, `factories.py`)
- [ ] Ready to implement M1 test

---

## Next Steps

1. [ ] Review and approve this document
2. [ ] Execute archival commands
3. [ ] Proceed to M1 implementation (TDD)
