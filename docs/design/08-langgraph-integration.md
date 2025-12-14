# Soni Framework - LangGraph Integration

## Overview

Soni uses LangGraph for dialogue management, leveraging its state graph execution, automatic checkpointing, and interrupt/resume patterns. This document details how Soni integrates with LangGraph correctly, following best practices and SOLID principles.

**Key Integration Points**:
- TypedDict-based state management
- Automatic persistence via checkpointers
- Human-in-the-loop via interrupt/resume
- Type-safe dependency injection
- Streaming for real-time updates

## Core LangGraph Patterns

### Automatic Checkpointing

LangGraph automatically saves state after each node execution:

```python
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.graph import StateGraph

# Create checkpointer
checkpointer = SqliteSaver.from_conn_string("dialogue_state.db")

# Compile graph with checkpointer
graph = builder.compile(checkpointer=checkpointer)

# State automatically saved per user via thread_id
config = {"configurable": {"thread_id": user_id}}
result = await graph.ainvoke(input_state, config=config)
```

**Key points**:
- ✅ State saved automatically after each node
- ✅ Each user isolated by `thread_id`
- ✅ No manual save/load needed
- ✅ Automatic resume from last position

### Thread Isolation

Each user conversation completely isolated:

```python
# User 1's conversation
await graph.ainvoke(
    input_state,
    config={"configurable": {"thread_id": "user_1"}}
)

# User 2's conversation (completely separate)
await graph.ainvoke(
    input_state,
    config={"configurable": {"thread_id": "user_2"}}
)
```

**Important**: No shared state between threads. For shared data, use external storage.

### interrupt() Pattern

Pause execution to wait for user input:

```python
from langgraph.types import interrupt

async def collect_slot_node(state: DialogueState) -> dict:
    """Ask for slot and pause execution"""

    # Get current flow from stack (idempotent operation)
    active_context = get_active_flow(state)
    current_flow_name = active_context["flow_name"] if active_context else "none"

    slot_config = get_slot_config(current_flow_name, next_slot)

    # Pause here - wait for user response
    user_response = interrupt({
        "type": "slot_request",
        "slot": next_slot,
        "prompt": slot_config.prompt
    })

    # Code after interrupt() executes when user responds
    return {
        "user_message": user_response,
        "waiting_for_slot": next_slot,
        "conversation_state": ConversationState.WAITING_FOR_SLOT.value
    }
```

**What happens**:
1. `interrupt()` raises `GraphInterrupt` exception
2. State saved with `next = ["collect_slot_node"]`
3. User receives prompt and responds
4. Graph resumed with `Command(resume=...)`
5. **CRITICAL**: Node **re-executes from the beginning**
6. The `interrupt()` returns the resume value instead of raising

**⚠️ Critical Note**: The entire node re-executes when resumed. Ensure all code before `interrupt()` is:
- **Idempotent**: Safe to run multiple times
- **Side-effect free**: No external state changes
- **Fast**: Expensive operations should be cached or moved after `interrupt()`

### Command(resume=) Pattern

Continue execution after interrupt:

```python
from langgraph.types import Command

async def process_message(msg: str, user_id: str) -> str:
    """Process message with automatic resumption"""

    config = {"configurable": {"thread_id": user_id}}

    # Check if interrupted
    current_state = await graph.aget_state(config)

    if current_state.next:
        # Interrupted - resume with user message
        result = await graph.ainvoke(
            Command(resume=msg),  # Pass value directly
            config=config
        )
    else:
        # New or completed conversation
        input_state = build_initial_state(msg)
        result = await graph.ainvoke(input_state, config=config)

    return result["last_response"]
```

**Key points**:
- ✅ `Command(resume=value)` passes value directly to `interrupt()`
- ✅ For single interrupt: `Command(resume="answer")`
- ✅ For multiple interrupts: Sequential `Command(resume=...)` calls
- ✅ LangGraph auto-loads checkpoint
- ✅ Only executes pending nodes

**Example with multiple interrupts**:

```python
async def node_with_multiple_interrupts(state: State) -> dict:
    """Node with multiple interrupts resolved sequentially"""

    # First interrupt
    name = interrupt("What is your name?")

    # Second interrupt
    age = interrupt("What is your age?")

    return {"name": name, "age": int(age)}

# Resume first interrupt
await graph.ainvoke(Command(resume="Alice"), config)
# Graph pauses at second interrupt

# Resume second interrupt
await graph.ainvoke(Command(resume="25"), config)
# Node completes
```

**Important**: Multiple interrupts are resolved in **order**, not by ID. LangGraph tracks the position automatically.

## Context Injection Pattern

LangGraph does not natively pass custom parameters to nodes. Soni uses one of two patterns for dependency injection.

### Dependency Requirements

- `langchain-core>=0.3.11` (for `AnyMessage` and message reducers such as `add_messages`)
- `langgraph>=0.2.x` (core framework)
- `aiosqlite` (only when using `AsyncSqliteSaver`)
- `asyncpg` (only when using `PostgresSaver`)
- `redis>=4.6.0` (only when using `RedisSaver`)
- `typing_extensions>=4.8.0` (for `Annotated` and modern type hints)

These dependencies must be defined in `pyproject.toml` to ensure the examples in this document compile without additional boilerplate.

### Pattern 1: context_schema (Recommended)

LangGraph 0.6+ supports type-safe runtime context:

```python
from langgraph.graph import StateGraph
from langgraph.runtime import Runtime
from typing import TypedDict

class RuntimeContext(TypedDict):
    """Runtime context with injected dependencies"""
    flow_manager: FlowManager
    nlu_provider: INLUProvider
    action_handler: IActionHandler
    scope_manager: IScopeManager
    normalizer: INormalizer

# Create graph with context schema
builder = StateGraph(
    state_schema=DialogueState,
    context_schema=RuntimeContext
)

# Node receives context via runtime parameter
async def understand_node(
    state: DialogueState,
    runtime: Runtime[RuntimeContext]
) -> dict:
    """
    Understand node with dependency injection.

    Args:
        state: Current dialogue state (TypedDict)
        runtime: Runtime context with injected dependencies

    Returns:
        Partial state updates (dict)
    """
    # Access injected dependencies (type-safe)
    flow_manager = runtime.context["flow_manager"]
    nlu_provider = runtime.context["nlu_provider"]

    # Use dependencies
    active_ctx = flow_manager.get_active_context(state)
    current_flow_name = active_ctx["flow_name"] if active_ctx else "none"

    # Build NLU context
    dialogue_context = build_nlu_context(state, flow_manager)

    # Call NLU
    nlu_result = await nlu_provider.understand(
        state["user_message"],
        dialogue_context
    )

    return {
        "nlu_result": nlu_result.model_dump(),
        "conversation_state": ConversationState.UNDERSTANDING.value,
        "last_nlu_call": time.time()
    }

# Invoke with context
result = await graph.ainvoke(
    input_state,
    config=config,
    context={
        "flow_manager": flow_manager,
        "nlu_provider": nlu_provider,
        "action_handler": action_handler,
        "scope_manager": scope_manager,
        "normalizer": normalizer
    }
)
```

**Advantages**:
- ✅ Type-safe access to dependencies
- ✅ Clear separation of state and context
- ✅ IDE autocomplete support
- ✅ Explicit dependency declarations

### Pattern 2: Configurable (Alternative)

Store dependencies in config for access via `get_config()`:

```python
from langgraph.config import get_config

async def understand_node(state: DialogueState) -> dict:
    """Node using configurable for dependencies"""

    # Get config at runtime
    config = get_config()

    # Access dependencies from configurable
    flow_manager = config["configurable"]["flow_manager"]
    nlu_provider = config["configurable"]["nlu_provider"]

    # Use dependencies
    active_ctx = flow_manager.get_active_context(state)
    # ... rest of logic

    return {"nlu_result": result.model_dump()}

# Invoke with dependencies in config
result = await graph.ainvoke(
    input_state,
    config={
        "configurable": {
            "thread_id": user_id,
            "flow_manager": flow_manager,
            "nlu_provider": nlu_provider
        }
    }
)
```

**Advantages**:
- ✅ Works with older LangGraph versions
- ✅ Flexible: can add dependencies without schema changes

**Disadvantages**:
- ⚠️ No type safety
- ⚠️ Runtime errors if dependency missing

### Pattern 3: No Dependencies (Simple Nodes)

For nodes that don't need external dependencies:

```python
async def simple_node(state: DialogueState) -> dict:
    """Node with no external dependencies"""

    # Pure computation on state
    value = state["some_field"] * 2

    return {"result": value}
```

### Recommendation

**Use `context_schema` (Pattern 1)** for Soni. It provides:
- Type safety (catches errors at development time)
- Clear dependency declarations
- Better maintainability
- Alignment with SOLID principles (Dependency Inversion)

## State Definition

### FlowContext Structure

Define the flow context structure used in the state:

```python
from typing import TypedDict, Literal

FlowState = Literal["active", "paused", "completed", "cancelled", "abandoned", "error"]

class FlowContext(TypedDict):
    """
    Context for a specific instance of a flow.

    See docs/design/07-flow-management.md for complete specification.
    """

    flow_id: str
    """Unique instance ID (e.g., 'book_flight_3a7f'). Key for flow_slots."""

    flow_name: str
    """Name of the flow definition (e.g., 'book_flight')."""

    flow_state: FlowState
    """Current execution state."""

    current_step: str | None
    """Current step identifier in the flow definition."""

    outputs: dict[str, Any]
    """Final outputs produced by this flow."""

    started_at: float
    """Unix timestamp when flow was started."""

    paused_at: float | None
    """Unix timestamp when flow was paused."""

    completed_at: float | None
    """Unix timestamp when flow completed."""

    context: str | None
    """Human-readable reason for pause/cancel."""
```

### DialogueState Schema

Complete state schema for LangGraph:

```python
from typing import TypedDict, Annotated, Any
from langchain_core.messages import AnyMessage
from langgraph.graph import add_messages

class DialogueState(TypedDict):
    """
    Complete dialogue state for LangGraph.

    MUST be TypedDict (not Pydantic BaseModel).
    All fields must be JSON-serializable.
    """

    # User communication
    user_message: str
    """Current user message being processed."""

    last_response: str
    """Last assistant response sent to user."""

    messages: Annotated[list[AnyMessage], add_messages]
    """
    Complete message history.
    Annotated with add_messages reducer for automatic merging.
    NOTE: Requires `langchain-core>=0.3.11` because LangGraph converts dicts to
    `AnyMessage` objects internally for ID tracking and serialization.
    """

    # Flow management
    flow_stack: list[FlowContext]
    """
    Active flow stack (LIFO).
    Bottom: Root/oldest flow
    Top: Currently active flow
    """

    flow_slots: dict[str, dict[str, Any]]
    """
    Flow-scoped slot storage.
    Key: flow_id (NOT flow_name)
    Value: dict of slot values
    """

    # State tracking
    conversation_state: str
    """
    Current conversation state (ConversationState enum value).
    Stored as string for JSON serialization.
    """

    current_step: str | None
    """Current step identifier in active flow."""

    waiting_for_slot: str | None
    """Slot name if waiting for user to provide value."""

    # NLU results
    nlu_result: dict[str, Any] | None
    """
    Latest NLU result (serialized).
    Stored as dict for JSON serialization.
    """

    last_nlu_call: float | None
    """Unix timestamp of last NLU invocation."""

    # Digression tracking
    digression_depth: int
    """Number of nested digressions."""

    last_digression_type: str | None
    """Type of last digression (question, help, etc)."""

    # Metadata
    turn_count: int
    """Total number of conversation turns."""

    trace: list[dict[str, Any]]
    """Execution trace for debugging and auditing."""

    metadata: dict[str, Any]
    """
    Archive and system metadata.
    Standard keys:
        - completed_flows: list[FlowContext]
        - error: str | None
    """
```

**Design Rationale**:
- **TypedDict**: Required by LangGraph (not Pydantic)
- **Annotated reducers**: For fields that merge (messages)
- **Flat structure**: All nested objects serialized to dict
- **Explicit types**: Every field fully typed for safety

## Node Implementation Patterns

Nodes in Soni follow one of three patterns based on dependency requirements.

### Pattern A: With Dependencies (Standard)

Most Soni nodes use dependency injection:

```python
from langgraph.runtime import Runtime

async def validate_slot_node(
    state: DialogueState,
    runtime: Runtime[RuntimeContext]
) -> dict:
    """
    Validate and normalize slot value.

    Pattern: With Dependencies (uses context_schema)

    Args:
        state: Current dialogue state
        runtime: Runtime context with dependencies

    Returns:
        Partial state updates
    """
    # Access dependencies
    flow_manager = runtime.context["flow_manager"]
    normalizer = runtime.context["normalizer"]

    # Get NLU result (deserialize)
    nlu_result = NLUOutput.model_validate(state["nlu_result"])
    slot_name = state["waiting_for_slot"]

    # Validate and normalize
    try:
        normalized = await normalizer.normalize(
            slot_name,
            nlu_result.slot_value
        )

        # Store in active flow
        flow_manager.set_slot(state, slot_name, normalized)

    return {
            "conversation_state": ConversationState.COLLECTING.value
        }

    except ValidationError as e:
        return {
            "last_response": f"Invalid value: {e.message}",
            "conversation_state": ConversationState.WAITING_FOR_SLOT.value
        }
```

### Pattern B: Simple Computation

For pure state transformations:

```python
async def increment_turn_node(state: DialogueState) -> dict:
    """
    Increment turn counter.

    Pattern: Simple Computation (no dependencies)

    Args:
        state: Current dialogue state

    Returns:
        Partial state updates
    """
    return {
        "turn_count": state["turn_count"] + 1,
        "last_nlu_call": time.time()
    }
```

### Pattern C: Conditional Routing

For routing functions (not nodes):

```python
def route_after_understand(state: DialogueState) -> str:
    """
    Route based on NLU result.

    Pattern: Routing Function (synchronous, returns node name)

    Args:
        state: Current dialogue state

    Returns:
        Name of next node to execute
    """
    nlu_result = state["nlu_result"]

    # Deserialize if needed
    if isinstance(nlu_result, dict):
        nlu_result = NLUOutput.model_validate(nlu_result)

    # Route based on NLU result
    if nlu_result.is_slot_value:
        return "validate_slot"
    elif nlu_result.is_digression:
        return "handle_digression"
    elif nlu_result.is_intent_change:
        return "handle_intent_change"
    else:
        return "generate_response"
```

**Pattern Summary**:

| Pattern | Use Case | Signature | Example |
|---------|----------|-----------|---------|
| A: With Dependencies | Most nodes | `(state, runtime) -> dict` | NLU, validation, actions |
| B: Simple | Pure computation | `(state) -> dict` | Counters, timestamps |
| C: Routing | Conditional edges | `(state) -> str` | Route decisions |

**Important**:
- All nodes return **partial updates** (dict), never full state
- All complex objects must be serialized (`.model_dump()`)
- Routing functions are sync, return node name (str)

## Graph Construction

```python
from langgraph.graph import StateGraph, START, END

def build_graph(
    config: SoniConfig,
    context: RuntimeContext
) -> CompiledGraph:
    """
    Build LangGraph from Soni configuration.

    Args:
        config: Soni configuration
        context: Runtime context with dependencies

    Returns:
        Compiled graph ready for execution
    """
    # Create graph with schemas
    builder = StateGraph(
        state_schema=DialogueState,
        context_schema=RuntimeContext
    )

    # Add nodes
    builder.add_node("understand", understand_node)
    builder.add_node("validate_slot", validate_slot_node)
    builder.add_node("handle_digression", handle_digression_node)
    builder.add_node("handle_intent_change", handle_intent_change_node)
    builder.add_node("collect_next_slot", collect_next_slot_node)
    builder.add_node("execute_action", execute_action_node)
    builder.add_node("generate_response", generate_response_node)

    # Entry point: START → understand (ALWAYS)
    builder.add_edge(START, "understand")

    # Conditional routing from understand
    builder.add_conditional_edges(
        "understand",
        route_after_understand,
        {
            "validate_slot": "validate_slot",
            "handle_digression": "handle_digression",
            "handle_intent_change": "handle_intent_change",
            "generate_response": "generate_response"
        }
    )

    # After digression, go to response generation (then END)
    # Digressions are handled as single-turn interactions
    builder.add_edge("handle_digression", "generate_response")

    # After validating slot
    builder.add_conditional_edges(
        "validate_slot",
        route_after_validate,
        {
            "execute_action": "execute_action",
            "collect_next_slot": "collect_next_slot"
        }
    )

    # After collecting slot, back to understand (wait for user input)
    builder.add_edge("collect_next_slot", "understand")

    # Action → response → END
    builder.add_edge("execute_action", "generate_response")
    builder.add_edge("generate_response", END)

    # Compile with checkpointer
    # soni.dm.builder.build_graph handles this logic
    return builder.compile(checkpointer=checkpointer)
```

**Design Principles**:
- **Single entry point**: All messages start at `understand`
- **Explicit routing**: Conditional edges for branching logic
- **Loop patterns**: Nodes can loop back to `understand`
- **Clear termination**: All paths eventually reach `END`
- **Builder Pattern**: The `soni.dm.builder` module is the single source of truth for graph construction.

## Checkpointer Backends

### InMemorySaver (Testing)

```python
from langgraph.checkpoint.memory import InMemorySaver

# Create in-memory checkpointer
checkpointer = InMemorySaver()

# Use with context manager (recommended)
with InMemorySaver() as checkpointer:
    graph = builder.compile(checkpointer=checkpointer)
    result = await graph.ainvoke(input_state, config)
```

**Characteristics**:
- ✅ **Sync & Async**: Supports both modes
- ✅ **Zero setup**: No external dependencies
- ✅ **Fast**: In-memory (no I/O)
- ⚠️ **Volatile**: Data lost when process ends

**Use for**:
- **Unit tests** (recommended)
- **Integration tests**
- Quick prototyping
- Debugging

### SQLite (Development)

**Option A: Async (Recommended)**

```python
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver

# Create async SQLite checkpointer
async with AsyncSqliteSaver.from_conn_string("dialogue_state.db") as checkpointer:
    graph = builder.compile(checkpointer=checkpointer)
    result = await graph.ainvoke(input_state, config)

# Or with explicit connection
import aiosqlite
async with aiosqlite.connect("dialogue_state.db") as conn:
    checkpointer = AsyncSqliteSaver(conn)
    graph = builder.compile(checkpointer=checkpointer)
    result = await graph.ainvoke(input_state, config)
```

**Requires**: `pip install aiosqlite`

**Characteristics**:
- ✅ **Fully async**: Native async support
- ✅ **Simple**: Single-file database
- ✅ **Persistent**: Data survives restarts
- ⚠️ **Single-writer**: Not for high concurrency

**Option B: Sync (Legacy)**

```python
from langgraph.checkpoint.sqlite import SqliteSaver

# Synchronous version (use only if you must)
with SqliteSaver.from_conn_string("dialogue_state.db") as checkpointer:
    graph = builder.compile(checkpointer=checkpointer)
    result = graph.invoke(input_state, config)  # Sync invoke
```

**Note**: Sync version blocks on I/O. Use `AsyncSqliteSaver` for async workflows.

**Use for**:
- Local development
- Single-user applications
- CI/CD pipelines

### PostgreSQL (Production - Async)

```python
from langgraph.checkpoint.postgres import PostgresSaver

# Create from connection string (async)
checkpointer = await PostgresSaver.from_conn_string(
    "postgresql://user:password@localhost:5432/soni"
)

# Or from existing pool
import asyncpg
pool = await asyncpg.create_pool("postgresql://...")
checkpointer = PostgresSaver(pool=pool)
```

**Characteristics**:
- ✅ **Fully async**: Native async support
- ✅ **Production-ready**: ACID transactions
- ✅ **Scalable**: Supports high concurrency

**Use for**:
- Production deployments
- Multi-instance applications
- High availability setups

### Redis (Production - High Performance)

```python
from langgraph.checkpoint.redis import RedisSaver
import redis.asyncio as redis

# Create Redis client
client = await redis.from_url("redis://localhost:6379")

# Create checkpointer
checkpointer = RedisSaver(client=client)
```

**Characteristics**:
- ✅ **Fully async**: Native async support
- ✅ **Very fast**: In-memory performance
- ⚠️ **Volatile**: Configure persistence for durability

**Use for**:
- High-performance requirements
- Distributed systems
- Session management with TTL

### Recommendation

For Soni deployments:

```python
async def create_checkpointer(config: SoniConfig) -> BaseCheckpointSaver:
    """Create checkpointer based on configuration"""

    backend = config.persistence.backend

    if backend == "memory":
        # Testing only
        return InMemorySaver()

    elif backend == "sqlite":
        # Development (async version)
        from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
        return AsyncSqliteSaver.from_conn_string(
            config.persistence.connection_string
        )

    elif backend == "postgresql":
        # Production (recommended)
        return await PostgresSaver.from_conn_string(
            config.persistence.connection_string
        )

    elif backend == "redis":
        # Production (high-performance)
        client = await redis.from_url(config.persistence.connection_string)
        return RedisSaver(client=client)

    else:
        raise ValueError(f"Unknown backend: {backend}")
```

## State Recovery

### Check Current State

```python
async def get_conversation_state(
    graph: CompiledGraph,
    user_id: str
) -> StateSnapshot:
    """Get current conversation state"""

    config = {"configurable": {"thread_id": user_id}}
    snapshot = await graph.aget_state(config)

    return snapshot
```

### Inspect State

```python
snapshot = await graph.aget_state(config)

# Check if interrupted
if snapshot.next:
    print(f"Waiting for user at: {snapshot.next}")
    print(f"Pending interrupts: {snapshot.interrupts}")

# Get current state
    print(f"Current state: {snapshot.values}")

# Get execution history
history = [
    checkpoint async for checkpoint in graph.aget_state_history(config)
]
print(f"Conversation has {len(history)} checkpoints")
```

### Resume from Specific Checkpoint

```python
# Get state history
checkpoints = []
async for checkpoint in graph.aget_state_history(config):
    checkpoints.append(checkpoint)

# Resume from specific checkpoint (5 turns ago)
target_checkpoint = checkpoints[5]
result = await graph.ainvoke(
    None,  # No input needed
    config={
        "configurable": {
            "thread_id": user_id,
            "checkpoint_id": target_checkpoint.config["configurable"]["checkpoint_id"]
        }
    }
)
```

**Use cases**:
- Time travel debugging
- Undo operations
- A/B testing different paths

## Node Lifecycle

### Execution Order

```
User sends message
  ↓
Check if interrupted (aget_state)
  ↓
If interrupted:
  - LangGraph loads checkpoint
  - Skips already-executed nodes
  - Starts from `next` nodes
  - Re-executes interrupted node from beginning
  ↓
Else:
  - Starts from START
  - Executes: START → understand → ...
  ↓
Execute pending nodes
  ↓
If interrupt() called:
  - Save checkpoint with `next = [...]`
  - Return control
  - State includes interrupts
  ↓
Else:
  - Execute until END
  - Mark conversation complete (next = ())
```

### Node Execution with Interrupt

```python
# Example node execution flow with interrupt

async def node_a(state: DialogueState) -> dict:
    # First execution: Do work
    result = compute_something(state)

    return {"field_a": result}
    # Checkpoint saved automatically
    # state["field_a"] = result

async def node_b(state: DialogueState) -> dict:
    # First execution
    print("Starting node_b")

    # Access field from node_a
    value_a = state["field_a"]

    # Pause execution
    user_input = interrupt({"prompt": "Please confirm?"})
    # Checkpoint saved with next = ["node_b"]
    # Execution pauses here
    # Control returns to caller

    # --- User responds ---
    # graph.ainvoke(Command(resume="yes"))

    # Second execution (after resume)
    print("Starting node_b")  # Prints AGAIN
    value_a = state["field_a"]  # Reads AGAIN
    user_input = ...  # Returns "yes" instead of raising

    # Now continues
    return {"field_b": user_input}
```

**Critical Understanding**:
1. Node executes up to `interrupt()`
2. State saved, execution pauses
3. On resume, node **re-executes from line 1**
4. All code before `interrupt()` runs again
5. `interrupt()` returns resume value instead of raising

## Error Handling

### Node Errors

```python
async def execute_action_node(
    state: DialogueState,
    runtime: Runtime[RuntimeContext]
) -> dict:
    """Execute action with comprehensive error handling"""

    try:
        # Get action handler
        action_handler = runtime.context["action_handler"]
        flow_manager = runtime.context["flow_manager"]

        # Get action name and inputs
        action_name = state["current_step"]

        # Get inputs from active flow
        active_ctx = flow_manager.get_active_context(state)
        if not active_ctx:
            raise ValueError("No active flow")

        inputs = state["flow_slots"].get(active_ctx["flow_id"], {})

        # Execute action
        result = await action_handler.execute(action_name, inputs)

        return {
            "conversation_state": ConversationState.COMPLETED.value,
            "metadata": {
                **state.get("metadata", {}),
                "action_result": result,
                "action_timestamp": time.time()
            }
        }

    except ActionNotFoundError as e:
        logger.error(f"Action not found: {e}", exc_info=True)
        return {
            "conversation_state": ConversationState.ERROR.value,
            "last_response": f"System error: Action '{action_name}' not found.",
            "metadata": {
                **state.get("metadata", {}),
                "error": str(e),
                "error_type": "action_not_found",
                "error_at": time.time()
            }
        }

    except ValidationError as e:
        logger.error(f"Action validation failed: {e}", exc_info=True)
        return {
            "conversation_state": ConversationState.ERROR.value,
            "last_response": "Some required information is invalid. Let's start over.",
            "metadata": {
                **state.get("metadata", {}),
                "error": str(e),
                "error_type": "validation_error",
                "error_at": time.time()
            }
        }

    except Exception as e:
        logger.error(f"Action failed: {e}", exc_info=True)
        return {
            "conversation_state": ConversationState.ERROR.value,
            "last_response": "Sorry, something went wrong. Please try again.",
            "metadata": {
                **state.get("metadata", {}),
                "error": str(e),
                "error_type": "unknown",
                "error_at": time.time()
            }
        }
```

### Error Recovery Nodes

```python
# Add error recovery node
builder.add_node("handle_error", handle_error_node)

# Route errors to recovery
builder.add_conditional_edges(
    "execute_action",
    lambda state: "handle_error" if state.get("metadata", {}).get("error") else "generate_response",
    {
        "handle_error": "handle_error",
        "generate_response": "generate_response"
    }
)

async def handle_error_node(
    state: DialogueState,
    runtime: Runtime[RuntimeContext]
) -> dict:
    """Handle errors and attempt recovery"""

    error = state.get("metadata", {}).get("error")
    error_type = state.get("metadata", {}).get("error_type")

    flow_manager = runtime.context["flow_manager"]

    # Attempt recovery based on error type
    if error_type == "validation_error":
        # Clear invalid data and retry
        flow_manager.pop_flow(state, result="cancelled")
        return {
            "last_response": "Let's try that again. What would you like to do?",
            "conversation_state": ConversationState.IDLE.value
        }

    elif error_type == "timeout":
        return {
            "last_response": "Request timed out. Would you like to try again?",
            "conversation_state": ConversationState.UNDERSTANDING.value
        }

    # Generic error - clear stack and start over
    return {
        "last_response": "Something went wrong. Let's start fresh.",
        "conversation_state": ConversationState.IDLE.value,
        "flow_stack": [],
        "flow_slots": {}
    }
```

### Errors After Interrupt

If a node fails AFTER resuming from interrupt:

```python
async def node_with_interrupt_and_error(
    state: DialogueState,
    runtime: Runtime[RuntimeContext]
) -> dict:
    """Node that might fail after interrupt"""

    try:
        # Get user input (idempotent)
        user_input = interrupt("Provide data:")

        # Risky operation (might fail)
        result = await risky_operation(user_input)

        return {"result": result}

    except RiskyOperationError as e:
        # Log error
        logger.error(f"Operation failed after interrupt: {e}")

        # Return error state (will be checkpointed)
        return {
            "conversation_state": ConversationState.ERROR.value,
            "error_message": str(e),
            "last_response": "Sorry, that didn't work. Let's try again."
        }
```

**Key point**: The node re-executes on resume, so the interrupt will be hit again before the risky operation. Wrap risky operations in try/except to handle failures gracefully.

## Streaming

LangGraph provides multiple streaming modes via `astream()`:

### Updates Streaming

Stream node updates as they complete:

```python
async def stream_node_updates(
    graph: CompiledGraph,
    msg: str,
    user_id: str
):
    """Stream node updates as they execute"""

    config = {"configurable": {"thread_id": user_id}}

    async for chunk in graph.astream(
        {"user_message": msg},
        config=config,
        stream_mode="updates"  # Default mode
    ):
        # chunk format: {node_name: update_dict}
        for node_name, update in chunk.items():
            if node_name != "__interrupt__":
                yield {
                    "type": "node_update",
                    "node": node_name,
                    "data": update
                }
```

**Use case**: Show progress to user ("Understanding your message...", "Executing action...")

### Values Streaming

Stream complete state after each step:

```python
async def stream_state_values(
    graph: CompiledGraph,
    msg: str,
    user_id: str
):
    """Stream complete state after each node execution"""

    config = {"configurable": {"thread_id": user_id}}

    async for state in graph.astream(
        {"user_message": msg},
        config=config,
        stream_mode="values"  # Full state after each step
    ):
        # state is the complete DialogueState dict
        yield {
            "type": "state_snapshot",
            "conversation_state": state.get("conversation_state"),
            "last_response": state.get("last_response"),
            "flow_stack_depth": len(state.get("flow_stack", []))
        }
```

**Use case**: Debugging, monitoring, real-time state visualization

### Debug Streaming

Stream checkpoints and task information:

```python
async def stream_debug_info(
    graph: CompiledGraph,
    msg: str,
    user_id: str
):
    """Stream debugging information"""

    config = {"configurable": {"thread_id": user_id}}

    async for event in graph.astream(
        {"user_message": msg},
        config=config,
        stream_mode="debug"  # Checkpoints + tasks
    ):
        # event includes checkpoint and task info
        yield {
            "type": "debug_event",
            "event": event
        }
```

**Use case**: Development debugging, performance profiling

### LLM Token Streaming

For streaming LLM tokens, use `stream_mode="messages"`:

```python
async def stream_llm_tokens(
    graph: CompiledGraph,
    msg: str,
    user_id: str
):
    """Stream LLM tokens as they are generated"""

    config = {"configurable": {"thread_id": user_id}}

    async for chunk in graph.astream(
        {"user_message": msg},
        config=config,
        stream_mode="messages"  # Token-by-token streaming
    ):
        # chunk format: tuple of (node_name, message_chunk)
        if len(chunk) == 2:
            node_name, message = chunk
            if hasattr(message, 'content') and message.content:
                yield {
                    "type": "token",
                    "content": message.content
                }
```

**Use case**: Real-time response generation, improved perceived latency

## Advanced Patterns

### Static Interrupts

Besides dynamic `interrupt()` calls, LangGraph supports static interruption points configured at compile time.

#### interrupt_before

Pause execution BEFORE a node runs:

```python
graph = builder.compile(
    checkpointer=checkpointer,
    interrupt_before=["execute_action"]  # Pause before executing action
)

# First invocation - pauses before execute_action
result = await graph.ainvoke(input_state, config)
# result["last_response"] contains pre-action message

# User reviews and approves
result = await graph.ainvoke(None, config)  # Continue from pause
# Now execute_action runs
```

**Use case**: Human approval before critical actions (payments, bookings, deletions)

#### interrupt_after

Pause execution AFTER a node completes:

```python
graph = builder.compile(
    checkpointer=checkpointer,
    interrupt_after=["collect_slot"]  # Pause after collecting slot
)

# Pauses after collect_slot completes
result = await graph.ainvoke(input_state, config)

# User can review collected data
# Continue when ready
result = await graph.ainvoke(None, config)
```

**Use case**: Review results before continuing (show collected slots for confirmation)

#### Wildcard Interrupts

Interrupt at all nodes:

```python
graph = builder.compile(
    checkpointer=checkpointer,
    interrupt_after="*"  # Pause after EVERY node
)
```

**Use case**: Step-through debugging, interactive testing

### Command.update Pattern

Update state fields WHILE resuming:

```python
async def process_with_metadata(
    graph: CompiledGraph,
    user_id: str,
    response: str
):
    """Resume and update metadata simultaneously"""

    config = {"configurable": {"thread_id": user_id}}

    # Resume AND update state
    result = await graph.ainvoke(
        Command(
            resume=response,
            update={
                "last_interaction": time.time(),
                "interaction_count": state["metadata"].get("interaction_count", 0) + 1
            }
        ),
        config
    )

    return result
```

**Use case**: Update metadata, tracking fields, or analytics while processing user input.

**Important**: The `update` is applied BEFORE the node re-executes.

### Command.goto Pattern

Direct the graph to a specific node explicitly:

```python
# Jump to specific node
await graph.ainvoke(
    Command(goto="handle_error"),
    config
)

# Jump to multiple nodes (parallel execution)
await graph.ainvoke(
    Command(goto=["node_a", "node_b"]),
    config
)

# Dynamic node invocation with Send
from langgraph.types import Send

await graph.ainvoke(
    Command(goto=Send("process_item", {"item": data})),
    config
)
```

**Use cases**:
- **Error recovery**: Jump to error handler
- **Dynamic routing**: Choose next node at runtime
- **Skip steps**: Bypass unnecessary nodes
- **Parallel processing**: Execute multiple nodes simultaneously

**Example - Error Recovery**:

```python
async def handle_timeout(
    graph: CompiledGraph,
    user_id: str
):
    """Handle timeout by jumping to recovery node"""

    config = {"configurable": {"thread_id": user_id}}

    # Check current state
    snapshot = await graph.aget_state(config)

    if snapshot.values.get("error_type") == "timeout":
        # Jump to retry logic
        result = await graph.ainvoke(
            Command(
                goto="retry_action",
                update={"retry_count": snapshot.values.get("retry_count", 0) + 1}
            ),
            config
        )
        return result
```

## Limitations and Considerations

### 1. JSON Serialization Required

All state must be JSON-serializable. LangGraph checkpointers serialize state to JSON.

```python
# ❌ BAD - Custom objects
class CustomObject:
    def __init__(self, value):
        self.value = value

state = {"data": CustomObject(42)}  # Fails at checkpoint

# ✅ GOOD - Primitive types or dicts
state = {"data": {"value": 42}}

# ✅ GOOD - Serialize Pydantic models
from pydantic import BaseModel

class MyModel(BaseModel):
    value: int

obj = MyModel(value=42)
state = {"data": obj.model_dump()}  # Serialized to dict
```

**Solution**: Always serialize complex objects with `.model_dump()` (Pydantic) or `.to_dict()` (custom).

### 2. thread_id is Mandatory

Checkpointers require `thread_id` for state isolation:

```python
# ❌ BAD - Missing thread_id
await graph.ainvoke(input_state)
# Raises: ValueError: "thread_id is required"

# ✅ GOOD - Always provide thread_id
config = {"configurable": {"thread_id": user_id}}
await graph.ainvoke(input_state, config)
```

**Solution**: Always pass `thread_id` in config. Use user ID, session ID, or conversation ID.

### 3. Node Re-execution Cost

Nodes re-execute COMPLETELY on resume. Expensive operations before `interrupt()` will run multiple times:

```python
async def expensive_node(state: DialogueState) -> dict:
    # This runs EVERY time, even on resume
    result = expensive_computation()  # ⚠️ Runs multiple times

    answer = interrupt("Question?")

    return {"result": answer}
```

**Solutions**:

**Option A: Move expensive operations after interrupt**:
```python
async def optimized_node(state: DialogueState) -> dict:
    # Get input first
    answer = interrupt("Question?")

    # Expensive operation AFTER interrupt (runs once)
    result = expensive_computation(answer)

    return {"result": result}
```

**Option B: Cache in state**:
```python
async def cached_node(state: DialogueState) -> dict:
    # Check if already computed
    if "expensive_result" not in state:
        result = expensive_computation()
        # Will be checkpointed
        return {"expensive_result": result}

    # Use cached result
    answer = interrupt("Question?")

    return {"result": answer}
```

### 4. No Cross-Thread State Sharing

Each `thread_id` is completely isolated. No shared state between users:

```python
# User 1
await graph.ainvoke(
    {"user_message": "hello"},
    {"configurable": {"thread_id": "user1"}}
)

# User 2 - CANNOT see user1's state
await graph.ainvoke(
    {"user_message": "hello"},
    {"configurable": {"thread_id": "user2"}}
)
```

**Solution**: For shared data (global settings, caches, etc.), use external storage:

```python
async def node_with_shared_data(
    state: DialogueState,
    runtime: Runtime[RuntimeContext]
) -> dict:
    # Get shared cache from context
    cache = runtime.context["shared_cache"]

    # Read shared data
    global_setting = await cache.get("global_setting")

    return {"setting": global_setting}
```

### 5. Checkpointer Performance

Different checkpointers have different performance characteristics:

| Backend | Type | Write Latency | Read Latency | Scalability | Use Case |
|---------|------|--------------|--------------|-------------|----------|
| InMemorySaver | Sync/Async | <1ms | <1ms | N/A | Testing |
| AsyncSqliteSaver | Async | ~2-5ms | ~1-3ms | Single instance | Development |
| SqliteSaver | Sync | ~1-5ms | ~1-5ms | Single instance | Legacy |
| PostgresSaver | Async | ~5-15ms | ~5-10ms | Horizontal | Production |
| RedisSaver | Async | ~1-3ms | ~1-3ms | Horizontal | High-perf |

**Recommendation**:
- **Testing**: `InMemorySaver` (fast, isolated tests)
- **Development**: `AsyncSqliteSaver` (simple, persistent)
- **Production (< 1000 users)**: `PostgresSaver` (durable, reliable)
- **Production (> 1000 users)**: `RedisSaver` (fast, scalable)
- **Production (critical data)**: `PostgresSaver` (ACID guarantees)

### 6. State Size Limits

Checkpointers may have size limits:

```python
# ❌ BAD - Storing large data in state
state = {
    "user_message": "hello",
    "large_file": base64_encode(10_mb_file)  # Too large
}

# ✅ GOOD - Store reference, data elsewhere
state = {
    "user_message": "hello",
    "file_id": "file_12345"  # Reference to external storage
}
```

**Recommendation**: Keep state < 1MB. Store large data (files, images) externally.

## Best Practices

### 1. Always Use TypedDict for State

```python
# ✅ GOOD
class DialogueState(TypedDict):
    user_message: str
    messages: list[dict]

# ❌ BAD
class DialogueState(BaseModel):  # Pydantic
    user_message: str
```

**Reason**: LangGraph requires TypedDict for state schema.

### 2. Return Updates, Not Full State

```python
# ✅ GOOD
async def node(state: DialogueState) -> dict:
    return {"field": "value"}  # Updates only

# ❌ BAD
async def node(state: DialogueState) -> DialogueState:
    state["field"] = "value"
    return state  # Full state
```

**Reason**: LangGraph merges updates automatically. Returning full state is redundant and error-prone.

### 3. Serialize Complex Objects

```python
# ✅ GOOD
return {
    "nlu_result": nlu_result.model_dump(),  # Pydantic
    "flow_stack": [f.copy() for f in flow_stack]  # Dicts
}

# ❌ BAD
return {
    "nlu_result": nlu_result,  # Object (not serializable)
    "flow_stack": flow_stack  # List of objects
}
```

**Reason**: Checkpointers serialize to JSON. Complex objects fail.

### 4. Use interrupt() for User Input

```python
# ✅ GOOD
user_response = interrupt({"prompt": "Question?"})

# ❌ BAD
# Trying to manually pause/resume
state["waiting_for_user"] = True
return state
```

**Reason**: `interrupt()` provides proper checkpoint and resume handling.

### 5. Check Interrupt State Correctly

```python
# ✅ GOOD
current_state = await graph.aget_state(config)
if current_state.next:
    result = await graph.ainvoke(Command(resume=data), config)

# ❌ BAD
# Manual tracking
if state.get("interrupted"):
    # ...
```

**Reason**: LangGraph tracks interrupts automatically via `next` field.

### 6. Use Correct Stream Modes

```python
# ✅ GOOD - Stream node updates
async for chunk in graph.astream(input, config, stream_mode="updates"):
    for node, update in chunk.items():
        print(f"{node}: {update}")

# ✅ GOOD - Stream full state
async for state in graph.astream(input, config, stream_mode="values"):
    print(f"State: {state}")

# ❌ BAD - astream_events is LangChain, not LangGraph
async for event in graph.astream_events(input, config):
    # This is NOT the LangGraph API
    pass
```

**Reason**: Use native LangGraph streaming API for correct behavior.

### 7. Make Pre-Interrupt Code Idempotent

```python
# ✅ GOOD - Idempotent operations
async def node(state: DialogueState) -> dict:
    # Reading is idempotent
    value = state["field"]
    computed = value * 2

    answer = interrupt("Question?")
    return {"result": answer}

# ❌ BAD - Side effects
async def node(state: DialogueState) -> dict:
    # External API call (runs multiple times!)
    await send_email(state["user_email"])

    answer = interrupt("Question?")
    return {"result": answer}
```

**Reason**: Nodes re-execute on resume. Side effects run multiple times.

### 8. Use context_schema for Dependencies

```python
# ✅ GOOD - Type-safe injection
graph = StateGraph(
    state_schema=DialogueState,
    context_schema=RuntimeContext
)

async def node(state: DialogueState, runtime: Runtime[RuntimeContext]) -> dict:
    manager = runtime.context["flow_manager"]
    return {}

# ❌ BAD - Manual injection via state
async def node(state: DialogueState) -> dict:
    manager = state["_flow_manager"]  # Pollutes state
    return {}
```

**Reason**: Separation of concerns. State is data, context is dependencies.

### 9. Handle Errors Gracefully

```python
# ✅ GOOD - Comprehensive error handling
async def node(state: DialogueState) -> dict:
    try:
        result = await risky_operation()
        return {"result": result}
    except SpecificError as e:
        logger.error(f"Error: {e}")
        return {
            "conversation_state": "error",
            "error_message": str(e)
        }

# ❌ BAD - Unhandled errors
async def node(state: DialogueState) -> dict:
    result = await risky_operation()  # May crash entire graph
    return {"result": result}
```

**Reason**: Errors in nodes crash the graph. Always handle expected errors.

### 10. Keep State Small

```python
# ✅ GOOD - Minimal state
state = {
    "user_id": "123",
    "last_message": "hello",
    "turn_count": 5
}

# ❌ BAD - Large embedded data
state = {
    "user_id": "123",
    "conversation_history": [...]  # 10,000 messages
    "user_profile": {...}  # Large object
}
```

**Reason**: State is checkpointed frequently. Keep it < 1MB for performance.

## Testing with InMemorySaver

For unit and integration tests, use `InMemorySaver` for fast, isolated testing:

### Basic Test Pattern

```python
import pytest
from langgraph.checkpoint.memory import InMemorySaver
from soni.graph import build_graph

@pytest.mark.asyncio
async def test_dialogue_flow():
    """Test complete dialogue flow"""

    # Arrange
    checkpointer = InMemorySaver()
    graph = build_graph(config, checkpointer=checkpointer)
    config = {"configurable": {"thread_id": "test-user-1"}}

    # Act
    result = await graph.ainvoke(
        {"user_message": "Book a flight"},
        config
    )

    # Assert
    assert result["conversation_state"] == "waiting_for_slot"
    assert result["last_response"] is not None
```

### Test with State Inspection

```python
@pytest.mark.asyncio
async def test_flow_stack_management():
    """Test flow stack push/pop"""

    # Arrange
    checkpointer = InMemorySaver()
    graph = build_graph(config, checkpointer=checkpointer)
    thread_config = {"configurable": {"thread_id": "test-user-1"}}

    # Act - Start flow
    await graph.ainvoke(
        {"user_message": "Book a flight"},
        thread_config
    )

    # Inspect state
    snapshot = await graph.aget_state(thread_config)
    assert len(snapshot.values["flow_stack"]) == 1
    assert snapshot.values["flow_stack"][0]["flow_name"] == "book_flight"

    # Act - Interrupt with new flow
    await graph.ainvoke(
        {"user_message": "Actually, check my booking first"},
        thread_config
    )

    # Inspect state again
    snapshot = await graph.aget_state(thread_config)
    assert len(snapshot.values["flow_stack"]) == 2
    assert snapshot.values["flow_stack"][-1]["flow_name"] == "check_booking"
```

### Test Interrupts and Resume

```python
@pytest.mark.asyncio
async def test_interrupt_resume():
    """Test interrupt and resume pattern"""

    # Arrange
    checkpointer = InMemorySaver()
    graph = build_graph(config, checkpointer=checkpointer)
    thread_config = {"configurable": {"thread_id": "test-user-1"}}

    # Act - Trigger interrupt
    result = await graph.ainvoke(
        {"user_message": "Book a flight"},
        thread_config
    )

    # Assert - Check interrupted
    snapshot = await graph.aget_state(thread_config)
    assert snapshot.next  # Has pending nodes
    assert len(snapshot.interrupts) > 0

    # Act - Resume
    from langgraph.types import Command
    result = await graph.ainvoke(
        Command(resume="New York"),
        thread_config
    )

    # Assert - Resumed successfully
    assert "New York" in result["flow_slots"]["book_flight"]["origin"]
```

### Parametrized Tests

```python
@pytest.mark.parametrize("user_input,expected_intent", [
    ("Book a flight", "book_flight"),
    ("Check my booking", "check_booking"),
    ("Cancel my reservation", "cancel_booking"),
])
@pytest.mark.asyncio
async def test_intent_recognition(user_input: str, expected_intent: str):
    """Test NLU intent recognition"""

    # Arrange
    checkpointer = InMemorySaver()
    graph = build_graph(config, checkpointer=checkpointer)
    thread_config = {"configurable": {"thread_id": f"test-{expected_intent}"}}

    # Act
    result = await graph.ainvoke(
        {"user_message": user_input},
        thread_config
    )

    # Assert
    assert result["flow_stack"][-1]["flow_name"] == expected_intent
```

### Fixture Pattern

```python
@pytest.fixture
async def graph_with_memory():
    """Fixture providing graph with InMemorySaver"""
    checkpointer = InMemorySaver()
    graph = build_graph(test_config, checkpointer=checkpointer)
    yield graph
    # Cleanup happens automatically

@pytest.mark.asyncio
async def test_with_fixture(graph_with_memory):
    """Test using fixture"""
    config = {"configurable": {"thread_id": "test-user"}}
    result = await graph_with_memory.ainvoke(
        {"user_message": "Hello"},
        config
    )
    assert result is not None
```

**Benefits of InMemorySaver for Testing**:
- ✅ **Fast**: No I/O overhead
- ✅ **Isolated**: Each test gets clean state
- ✅ **No setup**: No database required
- ✅ **Deterministic**: Repeatable results
- ✅ **Easy cleanup**: Automatic garbage collection

## Summary

LangGraph integration in Soni provides:

1. **Automatic checkpointing** - State saved after each node
2. **Thread isolation** - Each user completely separate
3. **interrupt()/Command(resume=)** - Human-in-the-loop pattern
4. **Flexible backends** - SQLite, PostgreSQL, Redis
5. **State recovery** - Access conversation history
6. **Error handling** - Graceful recovery from failures
7. **Multiple streaming modes** - updates, values, messages, debug
8. **Context injection** - Type-safe dependency injection via `context_schema`
9. **Static interrupts** - Compile-time pause points
10. **Advanced routing** - Command.goto for explicit navigation

These patterns enable robust, scalable dialogue management with minimal manual state management, following SOLID principles:

- **SRP**: Nodes have single responsibility, context separate from state
- **OCP**: Extensible via new nodes and checkpointer backends
- **LSP**: All checkpointers implement `BaseCheckpointSaver`
- **ISP**: Minimal interfaces (nodes just need `state` and optional `runtime`)
- **DIP**: Dependencies injected via `context_schema`, not hardcoded

## Next Steps

- **[04-state-machine.md](04-state-machine.md)** - DialogueState schema
- **[05-message-flow.md](05-message-flow.md)** - Message processing pipeline
- **[03-components.md](03-components.md)** - Component architecture
- **[07-flow-management.md](07-flow-management.md)** - Flow stack mechanics

---

**Design Version**: v1.0 (Complete, Zero-Legacy-Baggage)
**Status**: Production-ready design specification
**Last Updated**: 2024-12-03
**Verified Against**: LangGraph v0.2.x source code
**Design Philosophy**: Zero retrocompatibility, best practices first, SOLID principles
