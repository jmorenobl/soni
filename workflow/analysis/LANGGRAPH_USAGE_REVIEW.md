# LangGraph Usage Review - Soni Framework

**Date**: 2025-12-19
**Status**: Analysis Complete
**Reference**: `ref/langgraph/` (LangGraph source code)

---

## Executive Summary

This document analyzes how the Soni Framework uses LangGraph compared to the official patterns and APIs available in the reference implementation. The analysis identifies both correct usage patterns and opportunities for improvement.

**Key Findings:**
- Soni correctly implements the core StateGraph architecture
- Several advanced LangGraph features are not utilized
- Some patterns are implemented manually where official APIs exist

---

## 1. Current LangGraph Usage in Soni

### 1.1 Architecture Overview

Soni employs a **hierarchical two-level graph architecture**:

```
┌─────────────────────────────────────────────────────────────┐
│                    ORCHESTRATOR GRAPH                        │
│  (dm/builder.py)                                             │
│                                                              │
│   START → understand → execute → flow_{name} → resume → END │
│                           ↓                                  │
│                      ┌────┴────┐                            │
│                      │ respond │                            │
│                      └─────────┘                            │
└─────────────────────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                    FLOW SUBGRAPHS                            │
│  (compiler/subgraph.py)                                      │
│                                                              │
│   START → [step1] → [step2] → ... → __end_flow__ → END      │
│                                                              │
│   Step types: collect, action, say, set, branch, confirm    │
└─────────────────────────────────────────────────────────────┘
```

### 1.2 Files Using LangGraph (42 total)

| Component | File | LangGraph Usage |
|-----------|------|-----------------|
| **Core** | `runtime/loop.py` | Main orchestrator, graph invocation |
| **Builder** | `dm/builder.py` | StateGraph construction |
| **Compiler** | `compiler/subgraph.py` | Flow subgraph compilation |
| **Initializer** | `runtime/initializer.py` | Component wiring |
| **Checkpointer** | `runtime/checkpointer.py` | Persistence factory |
| **Nodes** | `dm/nodes/*.py` | Node implementations |
| **Node Factories** | `compiler/nodes/*.py` | Step type factories |

### 1.3 LangGraph Imports Used

```python
# Graph construction
from langgraph.graph import StateGraph, START, END
from langgraph.graph.state import CompiledStateGraph

# Dynamic routing
from langgraph.types import Command

# Message handling
from langgraph.graph.message import add_messages

# Checkpointing
from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.checkpoint.memory import MemorySaver
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
```

---

## 2. Patterns Correctly Implemented

### 2.1 StateGraph with TypedDict State

**Location**: `core/types.py`

```python
class DialogueState(TypedDict):
    messages: Annotated[list[AnyMessage], add_messages]  # ✅ Reducer
    flow_stack: list[FlowContext]
    flow_slots: dict[str, dict[str, Any]]
    flow_state: FlowState
    # ...
```

**Assessment**: ✅ Correct - Uses TypedDict with `add_messages` reducer as recommended.

### 2.2 Dynamic Routing with Command

**Location**: `dm/nodes/execute.py`

```python
def execute_node(state: DialogueState) -> Command:
    active_ctx = flow_manager.get_active_context(state)
    if active_ctx:
        target = get_flow_node_name(active_ctx["flow_name"])
        return Command(goto=target)
```

**Assessment**: ✅ Correct - Uses `Command(goto=...)` for runtime dispatch.

### 2.3 Conditional Edges

**Location**: `compiler/subgraph.py`

```python
def router(state: DialogueState) -> str:
    if is_waiting_input(state):
        return str(END)
    if state.get("_branch_target"):
        return str(state["_branch_target"])
    return target_node

builder.add_conditional_edges(node_name, router)
```

**Assessment**: ✅ Correct - Standard conditional routing pattern.

### 2.4 Checkpointer Factory

**Location**: `runtime/checkpointer.py`

```python
def create_checkpointer(backend: str) -> BaseCheckpointSaver:
    match backend:
        case "memory": return MemorySaver()
        case "sqlite": return AsyncSqliteSaver(...)
        case "postgres": return AsyncPostgresSaver(...)
```

**Assessment**: ✅ Correct - Supports all major backends.

### 2.5 Immutable State Updates (FlowDelta)

**Location**: `flow/manager.py`

```python
@dataclass
class FlowDelta:
    flow_stack: list[FlowContext] | None = None
    flow_slots: dict[str, dict[str, Any]] | None = None

def push_flow(state, flow_name) -> FlowDelta:
    # Returns delta, doesn't mutate state
    return FlowDelta(flow_stack=[...])
```

**Assessment**: ✅ Correct - Follows LangGraph's immutable update pattern.

---

## 3. Patterns NOT Utilized (Opportunities)

### 3.1 Context Schema (Official API)

**Reference Pattern** (`ref/langgraph/libs/langgraph/langgraph/graph/state.py`):

```python
# Official way to pass immutable runtime context
graph = StateGraph(
    state_schema=DialogueState,
    context_schema=RuntimeContext  # ← Not used by Soni
)
```

**Current Soni Implementation**:

```python
# Manual approach via configurable dict
config = {
    "configurable": {
        "thread_id": user_id,
        "runtime_context": RuntimeContext(...)  # Manual injection
    }
}
result = graph.ainvoke(payload, config=config)

# In nodes, manual extraction
def understand_node(state, config):
    context = config["configurable"]["runtime_context"]
```

**Recommendation**: Adopt `context_schema` for cleaner dependency injection:

```python
# Improved approach
graph = StateGraph(DialogueState, context_schema=RuntimeContext)

# In nodes
def understand_node(state: DialogueState, runtime: Runtime[RuntimeContext]):
    flow_manager = runtime.context.flow_manager
```

**Impact**: Medium - Cleaner API, better type safety, follows official patterns.

---

### 3.2 Runtime Dataclass

**Reference Pattern** (`ref/langgraph/libs/langgraph/langgraph/runtime.py`):

```python
@dataclass
class Runtime(Generic[ContextT]):
    context: ContextT          # Immutable user context
    store: BaseStore | None    # LangGraph store
    stream_writer: StreamWriter | None
    previous: ContextT | None  # Previous context
```

**Current Soni Implementation**: Not used - context accessed via `config["configurable"]`.

**Recommendation**: Use `Runtime[RuntimeContext]` in node signatures for cleaner access.

---

### 3.3 Send for Map-Reduce Patterns

**Reference Pattern** (`ref/langgraph/libs/langgraph/langgraph/types.py`):

```python
from langgraph.types import Send

def dispatcher(state: State) -> list[Send]:
    return [
        Send("worker", {"task": task})
        for task in state["pending_tasks"]
    ]
```

**Current Soni Implementation**: Not used.

**Potential Use Case**: Parallel slot validation or action execution:

```python
def validate_slots(state: DialogueState) -> list[Send]:
    return [
        Send("slot_validator", {"slot": slot, "value": value})
        for slot, value in state["pending_slots"].items()
    ]
```

**Impact**: Low - Current sequential processing is adequate for dialogue.

---

### 3.4 Interrupt Before/After (Human-in-the-Loop)

**Reference Pattern**:

```python
compiled = graph.compile(
    checkpointer=saver,
    interrupt_before=["review_node"],  # Official API
    interrupt_after=["sensitive_action"]
)

# Resume after human decision
state = graph.get_state(config)
# ... human review ...
result = graph.invoke({"decision": "approve"}, config)
```

**Current Soni Implementation**: Manual via `is_waiting_input(state)`:

```python
# Manual interrupt detection
def is_waiting_input(state: DialogueState) -> bool:
    return state.get("flow_state") == FlowState.WAITING_INPUT

# In router
if is_waiting_input(state):
    return END  # Manual "interrupt"
```

**Recommendation**: Consider using official `interrupt_before` for slot collection:

```python
compiled = graph.compile(
    checkpointer=saver,
    interrupt_before=["collect_slot"]  # Pause before slot collection
)
```

**Impact**: Medium - Official API is cleaner and handles edge cases better.

---

### 3.5 Durability Modes

**Reference Pattern**:

```python
Durability = Literal["sync", "async", "exit"]

compiled = graph.compile(
    checkpointer=saver,
    durability="async"  # Non-blocking persistence
)
```

- `"sync"`: Persist before next step (safe, slower)
- `"async"`: Persist while next step runs (efficient)
- `"exit"`: Persist only on exit (fast, risky)

**Current Soni Implementation**: Not configured - uses default (`"sync"`).

**Recommendation**: Consider `"async"` for production to improve latency.

**Impact**: Low - Performance optimization, not functional.

---

### 3.6 Streaming Modes

**Reference Pattern**:

```python
# Different streaming outputs
async for chunk in graph.astream(input, config, stream_mode="updates"):
    print(chunk)  # Only node-specific updates

async for chunk in graph.astream(input, config, stream_mode="messages"):
    print(chunk)  # Token-by-token LLM output
```

**Available Modes**:
- `"values"`: Full state after each step
- `"updates"`: Only node-specific updates
- `"checkpoints"`: Checkpoint snapshots
- `"debug"`: Tasks + checkpoints
- `"messages"`: Token streaming from LLMs
- `"custom"`: Via StreamWriter

**Current Soni Implementation**: Only uses `invoke()`, not streaming.

**Recommendation**: Implement streaming for better UX:

```python
# In RuntimeLoop
async def process_message_streaming(self, message: str):
    async for update in self.graph.astream(
        {"user_message": message},
        config=self.config,
        stream_mode="messages"
    ):
        yield update  # Stream tokens to client
```

**Impact**: High - Significantly improves user experience for long responses.

---

### 3.7 Store API

**Reference Pattern** (`ref/langgraph/libs/langgraph/langgraph/config.py`):

```python
from langgraph.config import get_store

def my_node(state: State):
    store = get_store()  # Access persistent key-value store
    user_prefs = store.get(("users", state["user_id"]), "preferences")
```

**Current Soni Implementation**: Not used - flow slots stored in state.

**Potential Use Case**: Persistent user preferences, cross-session memory.

**Impact**: Low for current use case.

---

## 4. Summary Comparison Table

| Feature | Reference Has | Soni Uses | Gap |
|---------|---------------|-----------|-----|
| StateGraph | ✅ | ✅ | None |
| TypedDict State | ✅ | ✅ | None |
| Reducers (add_messages) | ✅ | ✅ | None |
| Command routing | ✅ | ✅ | None |
| Conditional edges | ✅ | ✅ | None |
| Checkpointing | ✅ | ✅ | None |
| Subgraphs | ✅ | ✅ | None |
| **context_schema** | ✅ | ❌ | **Medium** |
| **Runtime dataclass** | ✅ | ❌ | **Medium** |
| **interrupt_before/after** | ✅ | ❌ Manual | **Medium** |
| **Streaming modes** | ✅ | ❌ | **High** |
| **Durability modes** | ✅ | ❌ | Low |
| Send (map-reduce) | ✅ | ❌ | Low |
| Store API | ✅ | ❌ | Low |

---

## 5. Recommended Actions

### Priority 1: High Impact

1. **Implement Streaming Support**
   - Add `astream()` with `stream_mode="messages"`
   - Stream LLM responses token-by-token to clients
   - Significantly improves perceived latency

### Priority 2: Medium Impact (Code Quality)

2. **Adopt `context_schema`**
   - Replace manual `configurable` injection
   - Use `Runtime[RuntimeContext]` in node signatures
   - Better type safety and cleaner code

3. **Use Official Interrupt API**
   - Replace manual `is_waiting_input` checks
   - Use `interrupt_before=["collect_slot"]`
   - Cleaner handling of pause/resume

### Priority 3: Low Impact (Performance)

4. **Configure Durability Mode**
   - Use `durability="async"` in production
   - Reduces checkpoint latency

5. **Consider Store API**
   - For future cross-session memory needs
   - User preferences persistence

---

## 6. Reference Files

For implementation details, consult:

| Topic | Reference Location |
|-------|-------------------|
| StateGraph API | `ref/langgraph/libs/langgraph/langgraph/graph/state.py` |
| Pregel Execution | `ref/langgraph/libs/langgraph/langgraph/pregel/main.py` |
| Types (Command, Send) | `ref/langgraph/libs/langgraph/langgraph/types.py` |
| Runtime Context | `ref/langgraph/libs/langgraph/langgraph/runtime.py` |
| Checkpointing | `ref/langgraph/libs/checkpoint/` |
| Examples | `ref/langgraph/examples/` |

---

## Appendix A: Current Soni Graph Structure

### Orchestrator Nodes

| Node | File | Purpose |
|------|------|---------|
| `understand` | `dm/nodes/understand.py` | Two-pass NLU (intent + slots) |
| `execute` | `dm/nodes/execute.py` | Route to active flow subgraph |
| `resume` | `dm/nodes/resume.py` | Flow completion, stack management |
| `respond` | `dm/nodes/respond.py` | Extract final response |
| `flow_{name}` | (compiled subgraphs) | Per-flow execution |

### Subgraph Node Factories

| Factory | Step Type | Purpose |
|---------|-----------|---------|
| `CollectNodeFactory` | `collect` | Slot value collection |
| `ActionNodeFactory` | `action` | Execute custom actions |
| `SayNodeFactory` | `say` | Send messages |
| `SetNodeFactory` | `set` | Set slot values |
| `BranchNodeFactory` | `branch` | Conditional routing |
| `ConfirmNodeFactory` | `confirm` | Confirmation flows |
| `WhileNodeFactory` | `while` | Loop handling |

---

**Last Updated**: 2025-12-19
**Maintained By**: Development Team
