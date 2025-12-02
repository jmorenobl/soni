# Architecture Overview

**Document Version**: 1.1
**Last Updated**: 2025-12-02
**Status**: Stable (with updates)

> **Note**: This document has been updated with final design decisions. For a complete summary of all final decisions and evolution, see [20-consolidated-design-decisions.md](20-consolidated-design-decisions.md).

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
- **Complex Conversation Support**: Flow stack for interruptions, digressions, and resumption
- **Context-Aware NLU**: Enriched prompts with conversation state, flow descriptions, paused flows
- **State Persistence**: Multi-turn conversations with automatic checkpointing
- **Extensible**: Plugin architecture for actions, validators, and NLU providers

### Problems Addressed in This Design

This redesign addresses critical structural issues in the original implementation:

1. ❌ **NLU called without context** → ✅ Context-enriched NLU with conversation state
2. ❌ **Graph re-executes from start on each message** → ✅ Resumable execution from current position
3. ❌ **No explicit conversation state tracking** → ✅ Explicit state machine with current_step
4. ❌ **Can't handle complex conversations** → ✅ Flow stack for interruptions and resumption
5. ❌ **No digression handling** → ✅ Digression detection and handling
6. ❌ **Poor error handling** → ✅ Comprehensive error recovery

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
- Provides rich context to NLU for better understanding
- Makes debugging and testing easier
- Provides clear conversation state for monitoring
- Supports flow stack management

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
- **Accuracy**: Provide rich context to NLU for better understanding
- **Flexibility**: Handle slot values, intent changes, digressions, resume requests
- **Simplicity**: Single code path for all message types
- **Context**: Include conversation state, flow descriptions, paused flows

**Decision Tree**:
```
Message received
  ↓
Call NLU to understand message
  ↓
NLU determines: slot value, intent change, or digression
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
│              Core Processing Layer                   │
│  RuntimeLoop (Orchestrator)                         │
│   - Message routing                                  │
│   - Flow stack helpers (push/pop)                   │
│   - Delegates to:                                    │
│     • DigressionHandler (coordinator)               │
│       ├─ KnowledgeBase (answers questions)          │
│       └─ HelpGenerator (generates help)             │
└────────────────────┬────────────────────────────────┘
                     │
        ┌────────────┴────────────┐
        │                         │
┌───────▼──────┐          ┌──────▼──────┐
│   NLU Layer  │          │ Graph Layer │
│              │          │             │
│ - DSPy/LLM   │          │ - LangGraph │
│ - Context    │          │ - Nodes     │
│ - Caching    │          │ - Routing   │
└───────┬──────┘          └──────┬──────┘
        │                         │
        └────────────┬────────────┘
                     │
┌────────────────────▼────────────────────────────────┐
│              State Management Layer                  │
│  - DialogueState (flow_stack, conversation_state)   │
│  - Checkpointer (SQLite/Postgres/Redis)             │
│  - Conversation history & Audit logs                │
└─────────────────────────────────────────────────────┘
```

### Data Flow (CORRECTED - LangGraph Pattern)

```
User Message
  ↓
RuntimeLoop.process_message()
  ↓
Check LangGraph State (aget_state)
  ├─ If interrupted → Resume with Command(resume=msg)
  └─ If new/completed → Invoke with initial state
  ↓
LangGraph Automatically:
  - Loads checkpoint if exists (by thread_id)
  - Resumes from last saved state
  - Skips already-executed nodes
  ↓
ALWAYS → Understand Node (NLU)
  ↓
NLU analyzes message with enriched context:
  - Current conversation state
  - Flow descriptions
  - Paused flows
  - Waiting for slot
  ↓
Conditional Routing (based on NLU result)
  ├─ Slot Value → Validate Node → Check if more slots needed
  ├─ Digression → Digression Node → Re-prompt → Back to Understand
  ├─ Intent Change → Intent Change Node → Push/Pop flow stack
  ├─ Resume Request → Resume Node → Pop to requested flow
  └─ Continue → Next Step Node
  ↓
Node Execution
  ↓
If need user input → interrupt() → Pause execution
  ↓
Update DialogueState (LangGraph auto-saves checkpoint)
  ↓
Generate Response
  ↓
Return response to user
  ↓
[Next user message loops back to top]
```

**Key Enhancements**:
- ✅ LangGraph automatic checkpointing and resumption
- ✅ Every message processed through NLU (unified pipeline)
- ✅ Flow stack management (push/pop) in state
- ✅ Digression handling without flow stack change
- ✅ Context-enriched NLU prompts
- ✅ Multiple result types from NLU (slot, digression, intent change, resume)
- ✅ `interrupt()` for pausing execution
- ✅ `Command(resume=)` for continuing after interrupt

---

## Component Responsibilities

### Runtime Loop (FINAL ARCHITECTURE)

**Responsibility**: Main orchestrator for message processing with context-aware routing and flow management.

**Design Philosophy**: RuntimeLoop is an **orchestrator**, not a God Object:
- Simple operations (push/pop flows) → Helper methods
- Complex domain logic (digressions) → Delegated to specialized components

**Architecture**:
```python
class RuntimeLoop:
    """
    Main orchestrator for conversation management.

    Delegates complex logic to specialized components while handling
    simple operations (flow stack) as helper methods.
    """

    def __init__(self, config, nlu_provider, graph, checkpointer):
        self.config = config
        self.nlu_provider = nlu_provider
        self.graph = graph
        self.checkpointer = checkpointer

        # Dependency injection for digression handling
        knowledge_base = KnowledgeBase(config)
        help_generator = HelpGenerator(config)
        self.digression_handler = DigressionHandler(knowledge_base, help_generator)
```

**Key Functions**:
```python
class RuntimeLoop:
    async def process_message(self, msg: str, user_id: str) -> str:
        """
        Main entry point for message processing.

        Uses LangGraph's checkpointing to automatically resume conversations.
        """
        config = {"configurable": {"thread_id": user_id}}

        # Check current state
        current_state = await self.graph.aget_state(config)

        if current_state.next:
            # Interrupted - resume with user message
            from langgraph.types import Command
            result = await self.graph.ainvoke(
                Command(resume={"user_message": msg}),
                config=config
            )
        else:
            # New or completed - start fresh
            input_state = {
                "user_message": msg,
                "messages": [],
                "slots": {},
                "flow_stack": [],
                # ... other initial state
            }
            result = await self.graph.ainvoke(input_state, config=config)

        return result["last_response"]

    # Flow stack helpers (simple list operations)
    def _push_flow(self, state: DialogueState, flow_name: str, reason: str = None):
        """Push new flow to stack, pausing current one"""

    def _pop_flow(self, state: DialogueState, result: FlowState = FlowState.COMPLETED):
        """Pop current flow and resume previous one"""

    def _get_active_flow(self, state: DialogueState) -> FlowContext | None:
        """Get currently active flow (top of stack)"""
```

**What Changed**:
- ❌ OLD: Always calls `graph.ainvoke(state)` from START, no checkpointing
- ✅ NEW: Uses LangGraph checkpointing for automatic resumption
- ✅ NEW: Every message processed through NLU first (even when waiting for slot)
- ✅ NEW: Flow stack operations as simple helpers (not separate class)
- ✅ NEW: Delegates digression handling to specialized components
- ✅ NEW: Supports flow interruption with `interrupt()` and resumption with `Command(resume=)`

### NLU Layer

**Responsibility**: Understand user intent, extract entities, detect digressions, identify resume requests.

**Key Functions**:
```python
class SoniDU(INLUProvider):
    async def predict(self, context: NLUContext) -> NLUResult:
        """
        Predict intent and extract slots with context awareness.

        Detects:
        - Slot values
        - Intent changes
        - Digressions (questions, clarifications, help)
        - Resume requests (return to paused flow)
        """

    def build_context(self, state: DialogueState) -> NLUContext:
        """Build enriched context for NLU (NEW)"""
```

**What Changed**:
- ❌ OLD: Always invoked on every turn without context
- ✅ NEW: Always invoked with enriched context including conversation_state, flow descriptions, paused flows

**NLU Result Structure**:
```python
@dataclass
class NLUResult:
    intent: str                           # Detected intent or flow name
    slots: dict[str, Any]                # Extracted slot values
    confidence: float                     # Overall confidence
    is_digression: bool                  # Is this a temporary deviation?
    digression_type: DigressionType | None  # Type of digression
    is_resume_request: bool              # Does user want to resume paused flow?
    resume_flow_name: str | None         # Which flow to resume
```

### Graph Layer (LangGraph)

**Responsibility**: Execute dialogue flow nodes with automatic checkpointing and resumption.

**Core Pattern**: Every message flows through the same pipeline:
```
User Message → Understand Node (NLU) → Conditional Routing → Action/Response
```

**Node Types**:
1. **Understand Node**: Always first - calls NLU to analyze user message
2. **Process Node**: Handles NLU results (slot validation, digression, intent change)
3. **Action Node**: Execute external actions
4. **Response Node**: Generate and return response to user

**Critical Design**:
- ✅ **Every message goes through NLU first** - even when waiting for a slot
- ✅ **Conditional edges** route based on NLU results
- ✅ **Checkpointing** handles persistence automatically
- ✅ **interrupt()** pauses execution to wait for user input

**What Changed**:
- ❌ OLD: Graph always executes from START
- ✅ NEW: Graph uses checkpointing to resume automatically from last saved state

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

### Flow Stack Management (INTEGRATED IN RUNTIMELOOP)

**Responsibility**: Manage flow stack for complex conversation patterns.

**Design Decision**: Flow stack operations are simple list manipulations, implemented as helper methods in RuntimeLoop rather than a separate class.

**Helper Methods**:
```python
# In RuntimeLoop class

def _push_flow(self, state: DialogueState, flow_name: str, reason: str = None):
    """
    Push new flow to stack, pausing current one.
    Simple list operation - no separate manager needed.
    """
    if state.flow_stack:
        state.flow_stack[-1].flow_state = FlowState.PAUSED
        state.flow_stack[-1].paused_at = time.time()
        state.flow_stack[-1].context = reason

    new_flow = FlowContext(
        flow_name=flow_name,
        flow_state=FlowState.ACTIVE,
        current_step=None,
        collected_slots={},
        started_at=time.time(),
    )
    state.flow_stack.append(new_flow)
    state.current_flow = flow_name

def _pop_flow(self, state: DialogueState, result: FlowState = FlowState.COMPLETED):
    """
    Pop current flow and resume previous one.
    Simple list operation - no separate manager needed.
    """
    if not state.flow_stack:
        raise ValueError("Cannot pop empty flow stack")

    current = state.flow_stack.pop()
    current.flow_state = result
    current.completed_at = time.time()

    state.metadata.setdefault("completed_flows", []).append(current)

    if state.flow_stack:
        previous = state.flow_stack[-1]
        previous.flow_state = FlowState.ACTIVE
        state.current_flow = previous.flow_name
    else:
        state.current_flow = "none"
```

**What it enables**:
- Flow interruptions (user starts new task mid-flow)
- Flow resumption (return to paused flow)
- Nested conversations
- Context preservation across flow switches

**Rationale**: These are straightforward list operations without complex domain logic, so they don't justify a separate class.

### Digression Handler (DECOMPOSED ARCHITECTURE)

**Responsibility**: Handle temporary deviations without changing flow state.

**Design Philosophy**: Decomposed into focused components following Single Responsibility Principle:

```python
class DigressionHandler:
    """
    Coordinator for digression handling.
    Delegates to specialized components based on digression type.
    """

    def __init__(self, knowledge_base: KnowledgeBase, help_generator: HelpGenerator):
        self.knowledge_base = knowledge_base
        self.help_generator = help_generator

    async def handle(
        self,
        state: DialogueState,
        digression_type: DigressionType,
        digression_topic: str,
    ) -> DialogueState:
        """
        Coordinate digression handling by delegating to appropriate component.
        """
        if digression_type == DigressionType.QUESTION:
            response = await self.knowledge_base.answer_question(digression_topic, state)
        elif digression_type in (DigressionType.CLARIFICATION, DigressionType.HELP):
            response = await self.help_generator.generate_help(state)
        # ... etc


class KnowledgeBase:
    """
    Answers domain-specific questions using knowledge base, RAG, or documentation.

    Can be extended with:
    - Vector database for semantic search
    - RAG pipeline for contextual answers
    - FAQ database
    """

    async def answer_question(self, topic: str, context: DialogueState) -> str:
        """Answer a domain-specific question"""


class HelpGenerator:
    """
    Generates contextual help and clarifications based on conversation state.
    """

    async def generate_help(self, state: DialogueState) -> str:
        """Generate contextual help message"""

    async def generate_status(self, state: DialogueState) -> str:
        """Generate status message showing what's been collected"""

    async def generate_clarification(self, topic: str, state: DialogueState) -> str:
        """Explain why we need certain information"""
```

**Digression Types**:
- Questions: "What cities do you support?"
- Clarifications: "Why do you need my date?"
- Help requests: "How does this work?"
- Status checks: "What information do you still need?"

**Benefits**:
- Single Responsibility: Each component has one clear purpose
- Extensibility: Easy to add RAG, knowledge bases, etc.
- Testability: Can test each component in isolation
- No God Object: Clear separation of concerns

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

**Problem**: Original design lacked context awareness and couldn't handle complex conversation patterns.

**Decision**: Implement context-aware NLU that understands conversation state and handles multiple scenarios.

**Alternatives Considered**:
1. ❌ Always call NLU without context: Less accurate, can't leverage conversation state
2. ❌ Simple regex/pattern matching: Can't handle intent changes, questions, corrections
3. ✅ **Context-aware NLU with enriched prompts**: Balances accuracy with efficiency

**Implementation**:
```python
async def _route_message(self, msg: str, state: DialogueState) -> MessageRoute:
    # Always call NLU with full context
    # NLU handles: slots, intents, digressions, resume requests
    return MessageRoute(
        type="nlu_understanding",
        context=self._build_nlu_context(state)
    )
```

**Note**: The NLU (DSPy module) is context-aware and can detect slot values, intent changes, questions, corrections, and resume requests based on conversation state.

### Decision 1.5: Critical Pattern - Always Through NLU First (NEW)

**Problem**: When waiting for a slot, user might not provide just the value - they might ask questions, correct themselves, or change their mind.

**Example**:
```
Bot: "Where would you like to fly from?"
User responses could be:
  - "New York" (simple slot value)
  - "What cities do you support?" (question/digression)
  - "Actually, I want to cancel" (intent change)
  - "Change the destination to LA first" (correction)
```

**Decision**: EVERY user message MUST pass through NLU first, even when waiting for a specific slot.

**Why This is Critical**:
```python
# ❌ WRONG - Assuming user provides slot value directly
def collect_slot_node(state):
    user_input = interrupt("Where would you like to fly from?")
    # PROBLEM: Assumes user_input is a city name
    # But user might say "What cities?" or "Cancel"
    state["slots"]["origin"] = user_input  # WRONG!
    return state

# ✅ CORRECT - Always through NLU first
def collect_slot_node(state):
    # Ask question and pause
    user_response = interrupt({
        "prompt": "Where would you like to fly from?",
        "waiting_for": "origin"
    })
    # User response GOES BACK TO understand_node first!
    return {"user_message": user_response, "waiting_for_slot": "origin"}

def understand_node(state):
    """ALWAYS processes user messages with NLU"""
    msg = state["user_message"]
    context = build_nlu_context(state)  # Includes waiting_for_slot

    # NLU with context understands ANY type of response
    nlu_result = await nlu.predict(msg, context)

    # Now we know what user said:
    if nlu_result.is_slot_value:
        return {"action": "validate_slot", "slot_value": nlu_result.value}
    elif nlu_result.is_digression:
        return {"action": "handle_digression", "question": nlu_result.topic}
    elif nlu_result.is_intent_change:
        return {"action": "change_intent", "new_intent": nlu_result.intent}
```

**LangGraph Implementation Pattern**:
```
┌─────────────────────────────────────────┐
│  User says ANYTHING                      │
│  (value, question, correction, cancel)   │
└─────────────────┬───────────────────────┘
                  │
                  ▼
         ┌────────────────┐
         │ Understand Node│  ← ALWAYS FIRST
         │    (NLU)       │
         └────────┬───────┘
                  │
                  ▼
    ┌─────────────────────────┐
    │  Conditional Routing    │
    └─────────────────────────┘
              │
    ┌─────────┴─────────────────────┐
    │                               │
    ▼                               ▼
┌──────────┐              ┌─────────────────┐
│Slot Value│              │Digression/Intent│
│Node      │              │Change Node      │
└──────────┘              └─────────────────┘
```

**Impact**: This pattern enables handling realistic human conversations where users don't always give direct answers.

---

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

    # NEW fields for state tracking
    conversation_state: ConversationState  # What are we doing?
    current_step: str | None               # Where are we in the flow?
    waiting_for_slot: str | None           # Which slot are we expecting?
    last_nlu_call: float | None            # Timestamp of last NLU call (for caching)

    # NEW fields for complex conversations
    flow_stack: list[FlowContext]          # Stack of flows (active + paused)
    digression_depth: int                  # How many digressions deep?
    last_digression_type: str | None       # Type of last digression
```

**FlowContext**:
```python
@dataclass
class FlowContext:
    """Complete context for a flow in the stack"""
    flow_name: str
    flow_state: FlowState  # ACTIVE, PAUSED, COMPLETED, CANCELLED
    current_step: str | None
    collected_slots: dict[str, Any]
    started_at: float
    paused_at: float | None = None
    context: str | None = None  # Why paused/cancelled
```

### Decision 3: Resumable Graph Execution with LangGraph Checkpointing (NEW)

**Problem**: Original design always started graph from START, even when resuming a conversation.

**Decision**: Leverage LangGraph's automatic checkpointing for seamless resumption.

**How LangGraph Checkpointing Works**:
1. **Automatic Saves**: LangGraph saves state after each node execution
2. **Thread Isolation**: Each user conversation has a unique `thread_id`
3. **Auto-Resume**: When invoking with the same `thread_id`, LangGraph automatically loads the last checkpoint
4. **No Manual Tracking**: No need to manually track `current_step` - LangGraph handles it

**Implementation Strategy**:
```python
async def process_message(self, msg: str, user_id: str) -> str:
    """
    Process message with automatic checkpoint resumption.

    LangGraph automatically:
    1. Loads last checkpoint for this thread_id
    2. Resumes from where it left off
    3. Only executes pending nodes
    """
    config = {"configurable": {"thread_id": user_id}}

    # Check if we're in the middle of an interrupted flow
    current_state = await self.graph.aget_state(config)

    if current_state.next:
        # We're waiting for user input (interrupted)
        # Resume with user's message
        from langgraph.types import Command
        result = await self.graph.ainvoke(
            Command(resume={"user_message": msg}),
            config=config
        )
    else:
        # New conversation or flow just completed
        input_state = self._build_initial_state(msg)
        result = await self.graph.ainvoke(input_state, config=config)

    return result["last_response"]
```

**Critical Pattern - Always Through NLU**:
```python
from langgraph.graph import StateGraph, START, END
from langgraph.types import interrupt

def understand_node(state: DialogueState):
    """
    ALWAYS the first node - processes ALL user messages with NLU.

    User can say:
    - "New York" (slot value)
    - "What cities do you support?" (question)
    - "Actually, I want to cancel" (intent change)

    NLU determines what it is.
    """
    user_message = state.get("user_message")

    # Build enriched context
    context = build_nlu_context(state)

    # Call NLU - understands ANY type of message
    nlu_result = await nlu_provider.predict(user_message, context)

    return {
        "nlu_result": nlu_result,
        "conversation_state": ConversationState.PROCESSING
    }

def route_after_understand(state: DialogueState) -> str:
    """Route based on NLU result"""
    result = state["nlu_result"]

    if result.is_slot_value:
        return "validate_slot"
    elif result.is_digression:
        return "handle_digression"
    elif result.is_intent_change:
        return "handle_intent_change"
    elif result.is_resume_request:
        return "handle_resume"
    else:
        return "generate_response"

def validate_slot_node(state: DialogueState):
    """Validate and store slot value"""
    nlu_result = state["nlu_result"]
    slot_name = state["waiting_for_slot"]
    value = nlu_result.slot_value

    # Validate
    if not validate_value(value, slot_name):
        return {
            "conversation_state": ConversationState.WAITING_FOR_SLOT,
            "last_response": f"Invalid {slot_name}. Please try again."
        }

    # Store validated slot
    state["slots"][slot_name] = value
    state["waiting_for_slot"] = None

    # Check if we need more slots or can proceed to action
    next_slot = get_next_required_slot(state)
    if next_slot:
        return {
            "conversation_state": ConversationState.WAITING_FOR_SLOT,
            "waiting_for_slot": next_slot,
            "last_response": f"Great! Now, {get_slot_prompt(next_slot)}"
        }
    else:
        return {
            "conversation_state": ConversationState.READY_FOR_ACTION
        }

def collect_next_slot_node(state: DialogueState):
    """
    Ask for the next required slot and PAUSE execution.
    Uses interrupt() to wait for user response.
    """
    next_slot = get_next_required_slot(state)

    if next_slot:
        # Pause here - wait for user input
        user_response = interrupt({
            "type": "slot_request",
            "slot": next_slot,
            "prompt": get_slot_prompt(next_slot)
        })

        # This code executes AFTER user responds
        # But user_response goes through understand_node first!
        return {
            "user_message": user_response,
            "waiting_for_slot": next_slot,
            "conversation_state": ConversationState.WAITING_FOR_SLOT
        }

    return state

# Build graph
builder = StateGraph(DialogueState)

# Add nodes
builder.add_node("understand", understand_node)  # ALWAYS FIRST
builder.add_node("validate_slot", validate_slot_node)
builder.add_node("handle_digression", handle_digression_node)
builder.add_node("collect_next_slot", collect_next_slot_node)
builder.add_node("execute_action", execute_action_node)
builder.add_node("generate_response", generate_response_node)

# Key pattern: START always goes to understand
builder.add_edge(START, "understand")

# Conditional routing from understand based on NLU result
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

# After handling digression, go back to understand
builder.add_edge("handle_digression", "understand")

# After validating slot, check if need more or ready for action
def route_after_validate(state: DialogueState) -> str:
    if state["conversation_state"] == ConversationState.READY_FOR_ACTION:
        return "execute_action"
    else:
        return "collect_next_slot"

builder.add_conditional_edges(
    "validate_slot",
    route_after_validate,
    {
        "execute_action": "execute_action",
        "collect_next_slot": "collect_next_slot"
    }
)

# After collecting next slot, back to understand (to process user's response)
builder.add_edge("collect_next_slot", "understand")

# After action, generate response and end
builder.add_edge("execute_action", "generate_response")
builder.add_edge("generate_response", END)

# Compile with checkpointer
from langgraph.checkpoint.sqlite import SqliteSaver
checkpointer = SqliteSaver.from_conn_string("dialogue_state.db")
graph = builder.compile(checkpointer=checkpointer)
```

**Benefits**:
- ✅ Automatic checkpoint save/load
- ✅ No manual state tracking needed
- ✅ Every message processed consistently through NLU
- ✅ Handles slot values, questions, corrections, intent changes uniformly
- ✅ interrupt() pauses until user responds
- ✅ Faster than re-executing completed nodes
- ✅ Lower cost (no redundant LLM calls)

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

### Decision 5: Slot Collection Strategies (UPDATED)

**Problem**: Original design always relied on NLU to extract slots, even when asking for a specific value.

**Initial Approach**: Proposed "direct mapping" with simple value detection (see early versions of docs 00-03).

**Revision**: After analysis, simple "direct mapping" found to be too simplistic - cannot distinguish "Boston" from "Actually, I want to cancel" using regex alone.

**Final Decision**: Unified NLU approach with context-aware prompting

**Single NLU Provider**: One DSPy module handles all understanding tasks:
- Slot value extraction
- Intent detection and changes
- Digression detection (questions, clarifications, corrections)
- Resume request identification

**Example**:
```python
async def process_message(self, msg: str, state: DialogueState) -> NLUResult:
    # Build enriched context with flow descriptions, paused flows, etc.
    context = self._build_nlu_context(state)

    # Single NLU call handles everything
    result = await self.nlu.predict(
        user_message=msg,
        context=context,
        waiting_for_slot=state.waiting_for_slot,
        conversation_state=state.conversation_state,
    )

    # Result includes:
    # - intent: detected intent or flow name
    # - slots: extracted slot values
    # - is_digression: whether this is a temporary deviation
    # - digression_type: question/clarification/help/etc
    # - confidence: overall confidence score

    return result
```

**Impact**: Simplified architecture, single optimization point, consistent behavior

**Reference**: See [20-consolidated-design-decisions.md](20-consolidated-design-decisions.md) for complete decision rationale

### Decision 6: Complex Conversation Management (NEW)

**Problem**: Users don't follow linear conversation paths - they interrupt, ask questions, change topics, and want to resume previous tasks.

**Decision**: Implement flow stack and digression handling for complex conversation patterns.

**Key Components**:

1. **Flow Stack**: LIFO stack of flows (active + paused)
   - Push new flow → pauses current flow
   - Pop flow → resumes previous flow
   - Preserves state across interruptions

2. **Digression Handler**: Handles temporary deviations
   - Questions about capabilities
   - Clarifications about requirements
   - Help requests
   - Does NOT change flow stack

**Example Flow Interruption**:
```python
# User starts booking
flow_stack = [FlowContext(flow_name="book_flight", flow_state=ACTIVE)]

# User interrupts to check existing booking
flow_stack.push(FlowContext(flow_name="check_booking", flow_state=ACTIVE))
# Previous flow paused: [book_flight(PAUSED), check_booking(ACTIVE)]

# After checking, return to booking
flow_stack.pop()  # check_booking COMPLETED
# Resume: [book_flight(ACTIVE)]
```

**Example Digression**:
```python
# Bot asks: "Where would you like to fly from?"
# User: "What cities do you support?"

# NLU detects digression
# Answer question + re-prompt original
# NO change to flow_stack

# Bot: "We support NYC, LA, Chicago, etc. Where would you like to fly from?"
```

**Benefits**:
- Natural conversation flow
- Context preservation
- User can return to interrupted tasks
- Handles realistic human behavior

**Reference**: See [05-complex-conversations.md](05-complex-conversations.md) for detailed design

---

## Summary

This redesign addresses the core structural issues in the original implementation by introducing:

1. ✅ **Explicit state machine** with conversation_state and current_step
2. ✅ **Critical Pattern: Always Through NLU First** - Every message processed by NLU, even when waiting for slot
3. ✅ **LangGraph Checkpointing** for automatic save/resume (NOT manual tracking)
4. ✅ **Unified context-aware NLU** with enriched prompts (includes waiting_for_slot, flow descriptions, paused flows)
5. ✅ **Flow stack management** as simple helpers (not separate class)
6. ✅ **Decomposed digression handling** (DigressionHandler → KnowledgeBase + HelpGenerator)
7. ✅ **interrupt() and Command(resume=)** for pausing/resuming execution

### Architecture Highlights

**LangGraph Integration**:
- ✅ **Automatic Checkpointing**: LangGraph saves state after each node
- ✅ **Thread Isolation**: Each user has unique `thread_id`
- ✅ **Auto-Resume**: Invoking with same `thread_id` loads last checkpoint
- ✅ **interrupt()**: Pauses execution to wait for user input
- ✅ **Conditional Edges**: Routes based on NLU results

**Clean Separation**:
- **RuntimeLoop**: Orchestrator with simple helpers (push/pop flows)
- **Understand Node**: ALWAYS first - processes all messages with NLU
- **DigressionHandler**: Coordinator that delegates to specialized components
- **KnowledgeBase**: Answers questions (can integrate RAG, vector DB)
- **HelpGenerator**: Generates contextual help and clarifications

**Critical Pattern**:
```
User Message → Understand Node (NLU) → Conditional Routing → Action/Response
              ↑                                              |
              └──────────────────────────────────────────────┘
              (Every message goes through NLU first)
```

**No God Objects**: Each component has focused responsibilities without becoming monolithic.

These changes maintain the strengths of the original design (LangGraph, DSPy, Zero-Leakage) while fixing architectural issues, using LangGraph correctly, and enabling complex conversation patterns with proper separation of concerns.

---

## Next Steps

1. Read [02-state-machine.md](02-state-machine.md) for detailed state schema and transitions
2. Read [03-message-processing.md](03-message-processing.md) for unified NLU message processing
3. Read [04-graph-execution-model.md](04-graph-execution-model.md) for LangGraph integration details (⚠️ needs update)
4. Read [05-complex-conversations.md](05-complex-conversations.md) for flow stack and digression handling
5. Read [06-flow-diagrams.md](06-flow-diagrams.md) for visual reference

**Important Notes**:
- ⚠️ Documents 03 and 04 may contain outdated LangGraph patterns - refer to this document for correct patterns
- ✅ Critical pattern: Always process user messages through NLU first
- ✅ Use LangGraph checkpointing for automatic resume (not manual `current_step` tracking)
- ✅ Use `interrupt()` to pause, `Command(resume=)` to continue

---

**Document Status**: ✅ Updated with correct LangGraph patterns
**Last Updated**: 2025-12-02
**Next Review**: After validating with LangGraph documentation
