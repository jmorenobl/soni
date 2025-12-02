# Architecture Overview

**Document Version**: 1.0
**Last Updated**: 2025-12-02
**Status**: Draft

## Table of Contents

1. [Executive Summary](#executive-summary)
2. [System Goals](#system-goals)
3. [Architecture Principles](#architecture-principles)
4. [High-Level Architecture](#high-level-architecture)
5. [Component Responsibilities](#component-responsibilities)
6. [Technology Stack](#technology-stack)
7. [Design Decisions](#design-decisions)

---

## Executive Summary

Soni is a **conversational dialogue system** designed to build task-oriented chatbots using a declarative YAML configuration combined with automatic prompt optimization via DSPy. The system uses LangGraph for dialogue management and supports complex multi-turn conversations with slot filling, action execution, and branching logic.

### Key Features

- **Declarative Flow Definition**: Define dialogue flows in YAML without writing Python code
- **Automatic Prompt Optimization**: Use DSPy to optimize NLU prompts for better accuracy
- **Zero-Leakage Architecture**: YAML describes semantics (WHAT), Python implements logic (HOW)
- **State Persistence**: Multi-turn conversations with automatic checkpointing
- **Extensible**: Plugin architecture for actions, validators, and NLU providers

### Problems Addressed in This Design

This redesign addresses critical structural issues in the original implementation:

1. ❌ **NLU called on every turn unnecessarily** → ✅ Context-aware NLU invocation
2. ❌ **Graph re-executes from start on each message** → ✅ Resumable execution from current position
3. ❌ **No explicit conversation state tracking** → ✅ Explicit state machine with current_step
4. ❌ **Inefficient token usage** → ✅ Caching and history management
5. ❌ **Poor error handling** → ✅ Comprehensive error recovery

---

## System Goals

### Primary Goals

1. **Correctness**: Dialogue flows execute correctly according to configuration
2. **Efficiency**: Minimize LLM calls, latency, and token usage
3. **Developer Experience**: Easy to configure, debug, and extend
4. **User Experience**: Natural, responsive conversations
5. **Scalability**: Support hundreds of concurrent conversations

### Non-Goals

- ❌ General-purpose chatbot (we focus on task-oriented dialogues)
- ❌ Multilingual support in v1.0 (English only for now)
- ❌ Voice/speech processing (text-only)
- ❌ Real-time streaming responses (async only)

---

## Architecture Principles

### 1. **Explicit State Machine** (NEW)

**Principle**: The system maintains an explicit state machine that tracks:
- Current flow
- Current step in the flow
- What the system is waiting for (slot, confirmation, action result)

**Rationale**:
- Enables context-aware message processing
- Allows skipping unnecessary NLU calls
- Makes debugging and testing easier
- Provides clear conversation state for monitoring

**Example**:
```python
class ConversationState(Enum):
    IDLE = "idle"                    # No active flow
    UNDERSTANDING = "understanding"   # Processing user intent
    WAITING_FOR_SLOT = "waiting_for_slot"  # Expecting slot value
    EXECUTING_ACTION = "executing_action"  # Running action
    CONFIRMING = "confirming"         # Asking for confirmation
```

### 2. **Context-Aware Execution** (NEW)

**Principle**: The system decides what to execute based on conversation context, not by always re-running the entire graph.

**Rationale**:
- **Efficiency**: Avoid redundant NLU calls when we know what we're waiting for
- **Performance**: Reduce latency by skipping unnecessary computation
- **Cost**: Save tokens by not passing full history to NLU every turn

**Decision Tree**:
```
Message received
  ↓
Is conversation_state == WAITING_FOR_SLOT?
  YES → Map message directly to slot
  NO → Call NLU to understand intent
```

### 3. **Resumable Graph Execution** (NEW)

**Principle**: The graph can resume execution from the current step, not always from START.

**Rationale**:
- Supports interactive conversations where user provides information incrementally
- Enables pausing and resuming flows at any point
- Allows the system to "remember" where it was in the conversation

**Implementation Strategy**:
- Use LangGraph's checkpointing to save `current_node`
- Add routing logic to decide entry point (START vs current_node)
- Track execution position in DialogueState

### 4. **Zero-Leakage Architecture** (RETAINED)

**Principle**: YAML configuration describes WHAT should happen (semantics), Python code implements HOW (logic).

**Rationale**:
- Business analysts can modify flows without coding
- Technical details (HTTP, regex, SQL) stay in Python
- Configuration remains readable and maintainable

**Example**:
```yaml
# YAML: Semantic contract
actions:
  search_flights:
    inputs: [origin, destination, date]
    outputs: [flights, price]
```

```python
# Python: Implementation
@ActionRegistry.register("search_flights")
async def search_flights(origin: str, destination: str, date: str):
    response = await http_client.get(f"https://api.example.com/flights?...")
    return {"flights": response["data"], "price": response["total_price"]}
```

### 5. **SOLID Principles** (RETAINED)

**Principle**: Use interfaces (Protocols) for dependency injection and testability.

**Rationale**:
- Components are loosely coupled
- Easy to test with mocks
- Easy to swap implementations (e.g., different NLU providers)

**Key Interfaces**:
```python
class INLUProvider(Protocol):
    async def predict(self, context: NLUContext) -> NLUResult: ...

class IActionHandler(Protocol):
    async def execute(self, action: str, inputs: dict[str, Any]) -> dict[str, Any]: ...

class IScopeManager(Protocol):
    def get_available_actions(self, state: DialogueState) -> list[str]: ...
```

### 6. **Async-First** (RETAINED)

**Principle**: Everything is async. No sync wrappers, no blocking I/O.

**Rationale**:
- Maximize concurrency and throughput
- Native support for streaming
- Modern Python best practices (3.11+)

---

## High-Level Architecture

### System Layers

```
┌─────────────────────────────────────────────────────┐
│                   User Interface                     │
│            (FastAPI, WebSocket, CLI)                 │
└────────────────────┬────────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────────┐
│              Runtime Loop (NEW)                      │
│  - Message routing                                   │
│  - Context-aware execution                           │
│  - State management                                  │
└────────────────────┬────────────────────────────────┘
                     │
        ┌────────────┴────────────┐
        │                         │
┌───────▼──────┐          ┌──────▼──────┐
│   NLU Layer  │          │ Graph Layer │
│              │          │             │
│ - DSPy/LLM   │          │ - LangGraph │
│ - Caching    │          │ - Nodes     │
│ - Scoping    │          │ - Routing   │
└───────┬──────┘          └──────┬──────┘
        │                         │
        └────────────┬────────────┘
                     │
┌────────────────────▼────────────────────────────────┐
│              Persistence Layer                       │
│  - State checkpointing (SQLite/Postgres/Redis)      │
│  - Conversation history                              │
│  - Audit logs                                        │
└─────────────────────────────────────────────────────┘
```

### Data Flow (NEW Design)

```
User Message
  ↓
RuntimeLoop.process_message()
  ↓
Load DialogueState from checkpoint
  ↓
Context Router (NEW)
  ├─ If WAITING_FOR_SLOT → Direct Mapping
  ├─ If EXECUTING_ACTION → Wait for action result
  └─ Else → Call NLU
  ↓
Determine Entry Point (NEW)
  ├─ If resuming → current_step
  └─ If new flow → START
  ↓
Execute Graph from entry point
  ↓
Node execution (Understand/Collect/Action/Branch)
  ↓
Update DialogueState
  ↓
Generate Response
  ↓
Save checkpoint
  ↓
Return response to user
```

---

## Component Responsibilities

### Runtime Loop (NEW DESIGN)

**Responsibility**: Orchestrate message processing with context-aware routing.

**Key Functions**:
```python
class RuntimeLoop:
    async def process_message(self, msg: str, user_id: str) -> str:
        """Main entry point for message processing"""

    async def _route_message(self, msg: str, state: DialogueState) -> MessageRoute:
        """Decide how to process message based on context (NEW)"""

    async def _execute_from_step(self, state: DialogueState, step: str) -> dict:
        """Resume execution from specific step (NEW)"""
```

**What Changed**:
- ❌ OLD: Always calls `graph.ainvoke(state)` from START
- ✅ NEW: Routes message based on conversation_state, may skip NLU

### NLU Layer

**Responsibility**: Understand user intent and extract entities.

**Key Functions**:
```python
class SoniDU(INLUProvider):
    async def predict(self, context: NLUContext) -> NLUResult:
        """Predict intent and extract slots"""

    async def should_invoke_nlu(self, state: DialogueState) -> bool:
        """Decide if NLU is needed (NEW)"""
```

**What Changed**:
- ❌ OLD: Always invoked on every turn
- ✅ NEW: Invoked conditionally based on conversation state

### Graph Layer (LangGraph)

**Responsibility**: Execute dialogue flow nodes.

**Node Types**:
1. **Understand Node**: Call NLU and update state
2. **Collect Node**: Request slot from user or validate existing value
3. **Action Node**: Execute external actions
4. **Branch Node**: Conditional routing based on state

**What Changed**:
- ❌ OLD: Graph always executes from START
- ✅ NEW: Graph can resume from current_step

### State Manager

**Responsibility**: Manage dialogue state persistence.

**Key Functions**:
```python
class StateManager:
    async def load_state(self, user_id: str) -> DialogueState:
        """Load state from checkpoint"""

    async def save_state(self, user_id: str, state: DialogueState):
        """Save state to checkpoint"""

    async def get_execution_position(self, state: DialogueState) -> str | None:
        """Get current execution position (NEW)"""
```

---

## Technology Stack

### Core Dependencies

| Component | Technology | Version | Rationale |
|-----------|-----------|---------|-----------|
| **Language** | Python | 3.11+ | Modern async, type hints, performance |
| **Dialogue Management** | LangGraph | 1.0.4+ | State graph, checkpointing, resumable execution |
| **NLU** | DSPy | 3.0.4+ | Automatic prompt optimization |
| **LLM Providers** | OpenAI, Anthropic | Latest | Fast NLU models (gpt-4o-mini, claude-3-haiku) |
| **Web Framework** | FastAPI | 0.122.0+ | Async, WebSocket, modern Python |
| **Persistence** | SQLite/Postgres/Redis | Latest | Flexible checkpointing backends |
| **Validation** | Pydantic | 2.12.5+ | Data validation, schema enforcement |

### Why These Choices?

**LangGraph**:
- Native support for state graphs and checkpointing
- Resumable execution (critical for our design)
- Built-in persistence layer
- Active development and community

**DSPy**:
- Automatic prompt optimization via metrics
- Reduces manual prompt engineering
- Supports multiple LLM providers
- Compiled modules are serializable

**FastAPI**:
- Native async support
- WebSocket for streaming
- Automatic API documentation
- Modern Python typing

---

## Design Decisions

### Decision 1: Context-Aware Message Routing (NEW)

**Problem**: Original design always called NLU on every turn, wasting tokens and adding latency.

**Decision**: Implement context-aware routing that skips NLU when system knows what it's waiting for.

**Alternatives Considered**:
1. ❌ Always call NLU (original): Inefficient, slow, expensive
2. ❌ Never call NLU in collect nodes: Can't handle intent changes
3. ✅ **Context-aware routing**: Balance between efficiency and flexibility

**Implementation**:
```python
async def _route_message(self, msg: str, state: DialogueState) -> MessageRoute:
    # If waiting for specific slot and message looks like a value (not an intent)
    if state.conversation_state == ConversationState.WAITING_FOR_SLOT:
        if not self._has_intent_markers(msg):
            # Direct mapping: skip NLU
            return MessageRoute(type="direct_slot_mapping", slot=state.waiting_for_slot)

    # Otherwise, call NLU
    return MessageRoute(type="nlu_understanding")
```

### Decision 2: Explicit Conversation State (NEW)

**Problem**: Original design had no explicit tracking of "where we are" in the conversation.

**Decision**: Add `conversation_state` and `current_step` to DialogueState.

**Rationale**:
- Makes debugging easier (can inspect state to see what system is doing)
- Enables context-aware routing
- Supports resumable execution
- Improves error handling (know what went wrong and where)

**Schema**:
```python
class DialogueState(TypedDict):
    # Existing fields
    messages: list[dict[str, str]]
    slots: dict[str, Any]
    current_flow: str

    # NEW fields
    conversation_state: ConversationState  # What are we doing?
    current_step: str | None               # Where are we in the flow?
    waiting_for_slot: str | None           # Which slot are we expecting?
    last_nlu_call: float | None            # Timestamp of last NLU call (for caching)
```

### Decision 3: Resumable Graph Execution (NEW)

**Problem**: Original design always started graph from START, even when resuming a conversation.

**Decision**: Enable resuming execution from current_step.

**Implementation Strategy**:
```python
async def _execute_graph(self, state: DialogueState) -> dict:
    if state.current_step and state.conversation_state == ConversationState.WAITING_FOR_SLOT:
        # Resume from current step
        return await self.graph.ainvoke_from_node(state, state.current_step)
    else:
        # Start from beginning (new flow or need NLU)
        return await self.graph.ainvoke(state)
```

**Benefits**:
- Skip unnecessary node executions
- Faster response times
- Lower cost (fewer LLM calls)

### Decision 4: Two-Level Caching for NLU (NEW)

**Problem**: NLU calls are expensive and often redundant.

**Decision**: Implement two-level caching:
1. **Turn-level cache**: Cache NLU result for same message within a turn
2. **Session-level cache**: Cache NLU result for same message in same conversation context

**Implementation**:
```python
class NLUCache:
    def get_cache_key(self, msg: str, context: NLUContext) -> str:
        return hashlib.sha256(
            f"{msg}:{context.current_flow}:{context.available_actions}".encode()
        ).hexdigest()

    async def get_or_predict(self, msg: str, context: NLUContext) -> NLUResult:
        key = self.get_cache_key(msg, context)
        if key in self.cache and not self._is_expired(key):
            return self.cache[key]

        result = await self.nlu_provider.predict(msg, context)
        self.cache[key] = result
        return result
```

### Decision 5: Slot Collection Strategies (NEW)

**Problem**: Original design always relied on NLU to extract slots, even when asking for a specific value.

**Decision**: Support multiple slot collection strategies:

1. **Direct Mapping**: When waiting for a specific slot, map message directly
2. **NLU Extraction**: When processing general user input, extract via NLU
3. **Hybrid**: Use direct mapping with NLU fallback for ambiguous cases

**Example**:
```python
async def collect_slot(self, slot_name: str, state: DialogueState) -> SlotValue:
    user_msg = state.messages[-1]["content"]

    # Strategy 1: Direct mapping (if we just asked for this slot)
    if state.waiting_for_slot == slot_name:
        if self._is_simple_value(user_msg):
            return await self._normalize_slot_value(slot_name, user_msg)

    # Strategy 2: NLU extraction (if user provides complex input)
    nlu_result = await self.nlu.predict(...)
    return nlu_result.slots.get(slot_name)
```

---

## Summary

This redesign addresses the core structural issues in the original implementation by introducing:

1. ✅ **Explicit state machine** with conversation_state and current_step
2. ✅ **Context-aware routing** that skips unnecessary NLU calls
3. ✅ **Resumable graph execution** from current position
4. ✅ **NLU caching** to reduce redundant LLM calls
5. ✅ **Flexible slot collection** with multiple strategies

These changes maintain the strengths of the original design (LangGraph, DSPy, Zero-Leakage) while fixing performance and architectural issues.

---

## Next Steps

1. Read [02-state-machine.md](02-state-machine.md) for detailed state schema and transitions
2. Read [03-message-processing.md](03-message-processing.md) for message routing logic
3. Read [04-graph-execution-model.md](04-graph-execution-model.md) for LangGraph integration details

---

**Document Status**: Ready for review and implementation planning
**Next Review**: After implementation roadmap completion
