# Soni Framework - LangGraph Integration

## Overview

Soni uses LangGraph for dialogue management, leveraging its state graph execution, automatic checkpointing, and interrupt/resume patterns. This document details how Soni integrates with LangGraph correctly.

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

### interrupt() Pattern

Pause execution to wait for user input:

```python
from langgraph.types import interrupt

async def collect_slot_node(state: DialogueState) -> DialogueState:
    """Ask for slot and pause execution"""

    slot_config = get_slot_config(state.current_flow, next_slot)

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
        "conversation_state": ConversationState.WAITING_FOR_SLOT
    }
```

**What happens**:
1. `interrupt()` pauses execution and returns control
2. State saved with `next = ["collect_slot_node"]`
3. User receives prompt, responds
4. Graph resumed with `Command(resume=...)`
5. Execution continues from `interrupt()` with user's response

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
            Command(resume={"user_message": msg}),
            config=config
        )
    else:
        # New or completed conversation
        input_state = build_initial_state(msg)
        result = await graph.ainvoke(input_state, config=config)

    return result["last_response"]
```

**Key points**:
- ✅ `Command(resume=...)` continues from `interrupt()`
- ✅ LangGraph auto-loads checkpoint
- ✅ Only executes pending nodes
- ✅ No manual tracking needed

## Graph Construction

### State Definition

```python
from typing import TypedDict, Annotated
from langgraph.graph import add_messages

class DialogueState(TypedDict):
    """LangGraph state (must be TypedDict)"""

    # User communication
    user_message: str
    last_response: str
    messages: Annotated[list[dict], add_messages]

    # Flow management
    current_flow: str
    flow_stack: list[dict]  # Serialized FlowContext objects
    flow_slots: dict[str, dict[str, Any]]

    # State tracking
    conversation_state: str  # ConversationState enum value
    current_step: str | None
    waiting_for_slot: str | None

    # NLU results
    nlu_result: dict | None
    last_nlu_call: float | None

    # Metadata
    turn_count: int
    trace: list[dict]
    metadata: dict[str, Any]
    digression_depth: int
    last_digression_type: str | None
```

### Node Implementation

All nodes must be async and return state updates:

```python
async def understand_node(state: DialogueState) -> DialogueState:
    """
    Understand node - ALWAYS first.

    Returns dict with state updates (not full state).
    """
    user_message = state["user_message"]

    # Build context
    context = await build_nlu_context(state)

    # Call NLU
    nlu_result = await nlu_provider.predict(user_message, context)

    # Return updates
    return {
        "nlu_result": nlu_result.to_dict(),  # Serialize for checkpoint
        "conversation_state": ConversationState.UNDERSTANDING.value,
        "last_nlu_call": time.time()
    }
```

**Important**: Nodes return dict with **updates**, not full state. LangGraph merges updates into state.

### Graph Building

```python
from langgraph.graph import StateGraph, START, END

def build_graph(config: SoniConfig) -> CompiledGraph:
    """Build LangGraph from Soni configuration"""

    # Create graph
    builder = StateGraph(DialogueState)

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

    # After digression, back to understand
    builder.add_edge("handle_digression", "understand")

    # After validating slot
    builder.add_conditional_edges(
        "validate_slot",
        route_after_validate,
        {
            "execute_action": "execute_action",
            "collect_next_slot": "collect_next_slot"
        }
    )

    # After collecting slot, back to understand
    builder.add_edge("collect_next_slot", "understand")

    # Action → response → END
    builder.add_edge("execute_action", "generate_response")
    builder.add_edge("generate_response", END)

    # Compile with checkpointer
    checkpointer = SqliteSaver.from_conn_string("dialogue_state.db")
    return builder.compile(checkpointer=checkpointer)
```

### Conditional Routing

```python
def route_after_understand(state: DialogueState) -> str:
    """Route based on NLU result"""

    nlu_result = state["nlu_result"]

    # Deserialize if needed
    if isinstance(nlu_result, dict):
        nlu_result = NLUResult.from_dict(nlu_result)

    if nlu_result.is_slot_value:
        return "validate_slot"
    elif nlu_result.is_digression:
        return "handle_digression"
    elif nlu_result.is_intent_change:
        return "handle_intent_change"
    else:
        return "generate_response"

def route_after_validate(state: DialogueState) -> str:
    """Route after slot validation"""

    conv_state = ConversationState(state["conversation_state"])

    if conv_state == ConversationState.READY_FOR_ACTION:
        return "execute_action"
    else:
        return "collect_next_slot"
```

## Checkpointer Backends

### SQLite (Development)

```python
from langgraph.checkpoint.sqlite import SqliteSaver

# Create from connection string
checkpointer = SqliteSaver.from_conn_string("dialogue_state.db")

# Or from existing connection
import sqlite3
conn = sqlite3.connect("dialogue_state.db")
checkpointer = SqliteSaver(conn=conn)
```

**Use for**:
- Local development
- Testing
- Small deployments

### PostgreSQL (Production)

```python
from langgraph.checkpoint.postgres import PostgresSaver

# Create from connection string
checkpointer = PostgresSaver.from_conn_string(
    "postgresql://user:password@localhost:5432/soni"
)

# Or from existing pool
import asyncpg
pool = await asyncpg.create_pool("postgresql://...")
checkpointer = PostgresSaver(pool=pool)
```

**Use for**:
- Production deployments
- High concurrency
- Distributed systems

### Redis (High-Performance)

```python
from langgraph.checkpoint.redis import RedisSaver
import redis.asyncio as redis

# Create Redis client
client = await redis.from_url("redis://localhost:6379")

# Create checkpointer
checkpointer = RedisSaver(client=client)
```

**Use for**:
- High-performance requirements
- Distributed systems
- Session management

## State Recovery

### Check Current State

```python
async def get_conversation_state(user_id: str) -> StateSnapshot:
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

# Resume from specific checkpoint
target_checkpoint = checkpoints[5]  # 5 turns ago
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
  ↓
Else:
  - Execute until END
  - Mark conversation complete
```

### Node Execution

```python
# Example node execution flow

async def node_a(state):
    # Do work
    return {"field_a": "value_a"}
    # Checkpoint saved automatically
    # state.field_a = "value_a"

async def node_b(state):
    # Access field from node_a
    print(state["field_a"])  # "value_a"

    # Pause execution
    user_input = interrupt({"prompt": "Question?"})
    # Checkpoint saved with next = ["node_b"]
    # Execution pauses here

    # After resume, execution continues
    return {"field_b": user_input}
```

## Error Handling

### Node Errors

```python
async def execute_action_node(state: DialogueState) -> DialogueState:
    """Execute action with error handling"""

    try:
        action_name = state["current_step"]
        action_handler = ActionRegistry.get(action_name)

        # Get inputs from flow-scoped slots
        inputs = _get_action_inputs(state)

        # Execute action
        result = await action_handler.execute(action_name, inputs)

        return {
            "conversation_state": ConversationState.COMPLETED.value,
            "metadata": {**state.get("metadata", {}), "action_result": result}
        }

    except Exception as e:
        # Log error
        logger.error(f"Action failed: {e}", exc_info=True)

        # Update state
        return {
            "conversation_state": ConversationState.ERROR.value,
            "last_response": "Sorry, something went wrong. Please try again.",
            "metadata": {
                **state.get("metadata", {}),
                "error": str(e),
                "error_at": time.time()
            }
        }
```

### Recovery Nodes

```python
# Add error recovery node
builder.add_node("handle_error", handle_error_node)

# Route errors to recovery
builder.add_conditional_edges(
    "execute_action",
    lambda state: "handle_error" if state.get("error") else "generate_response",
    {
        "handle_error": "handle_error",
        "generate_response": "generate_response"
    }
)

async def handle_error_node(state: DialogueState) -> DialogueState:
    """Handle errors and attempt recovery"""

    error = state.get("metadata", {}).get("error")

    # Attempt recovery based on error type
    if "timeout" in str(error).lower():
        return {
            "last_response": "Request timed out. Would you like to try again?",
            "conversation_state": ConversationState.UNDERSTANDING.value
        }

    # Generic error
    return {
        "last_response": "Something went wrong. Let's start over.",
        "conversation_state": ConversationState.IDLE.value,
        "flow_stack": []  # Clear stack
    }
```

## Streaming

### Event Streaming

```python
async def process_message_stream(msg: str, user_id: str):
    """Process message with event streaming"""

    config = {"configurable": {"thread_id": user_id}}

    # Stream events
    async for event in graph.astream_events(
        {"user_message": msg},
        config=config,
        version="v1"
    ):
        event_type = event["event"]

        if event_type == "on_chain_start":
            node_name = event["name"]
            print(f"Starting: {node_name}")

        elif event_type == "on_chain_end":
            node_name = event["name"]
            output = event["data"]["output"]
            print(f"Completed: {node_name} → {output}")

        elif event_type == "on_llm_stream":
            chunk = event["data"]["chunk"]
            yield chunk  # Stream to client
```

### Token Streaming

```python
async def stream_response(msg: str, user_id: str):
    """Stream response tokens to client"""

    config = {"configurable": {"thread_id": user_id}}

    async for chunk in graph.astream(
        {"user_message": msg},
        config=config,
        stream_mode="values"
    ):
        if "last_response" in chunk:
            # Stream response incrementally
            response = chunk["last_response"]
            for token in response.split():
                yield f"{token} "
                await asyncio.sleep(0.05)  # Simulate streaming
```

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

### 2. Return Updates, Not Full State

```python
# ✅ GOOD
async def node(state):
    return {"field": "value"}  # Updates only

# ❌ BAD
async def node(state):
    state["field"] = "value"
    return state  # Full state
```

### 3. Serialize Complex Objects

```python
# ✅ GOOD
return {
    "nlu_result": nlu_result.to_dict(),  # Serializable
    "flow_stack": [f.to_dict() for f in flow_stack]
}

# ❌ BAD
return {
    "nlu_result": nlu_result,  # Object (not serializable)
    "flow_stack": flow_stack  # List of objects
}
```

### 4. Use interrupt() for User Input

```python
# ✅ GOOD
user_response = interrupt({"prompt": "Question?"})

# ❌ BAD
# Trying to manually pause/resume
state["waiting_for_user"] = True
return state
```

### 5. Check interrupt State Correctly

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

## Summary

LangGraph integration in Soni provides:

1. **Automatic checkpointing** - State saved after each node
2. **Thread isolation** - Each user completely separate
3. **interrupt()/Command(resume=)** - Pause/resume pattern
4. **Flexible backends** - SQLite, PostgreSQL, Redis
5. **State recovery** - Access conversation history
6. **Error handling** - Graceful recovery from failures
7. **Streaming** - Event and token streaming

These patterns enable robust, scalable dialogue management with minimal manual state management.

## Next Steps

- **[04-state-machine.md](04-state-machine.md)** - DialogueState schema
- **[05-message-flow.md](05-message-flow.md)** - Message processing pipeline
- **[03-components.md](03-components.md)** - Component architecture

---

**Design Version**: v0.8 (Production-Ready with Structured Types)
**Status**: Production-ready design specification
