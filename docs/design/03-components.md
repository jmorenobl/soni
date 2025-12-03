# Soni Framework - Components

## Overview

Soni's architecture is built around focused, single-responsibility components that work together to enable sophisticated conversational AI. This document details each component's responsibilities, interfaces, and implementation patterns.

## RuntimeLoop

### Responsibility

Main orchestrator for conversation management. Coordinates message processing, flow management, and delegation to specialized components.

### Design Philosophy

RuntimeLoop is an **orchestrator**, not a God Object:
- **Simple operations** (push/pop flows) → Implemented as helper methods
- **Complex domain logic** (digressions, knowledge retrieval) → Delegated to specialized components

### Architecture

```python
class RuntimeLoop:
    """
    Main orchestrator for conversation management.

    Delegates complex logic to specialized components while handling
    simple operations (flow stack) as helper methods.
    """

    def __init__(
        self,
        config: SoniConfig,
        nlu_provider: INLUProvider,
        graph: CompiledGraph,
        checkpointer: BaseCheckpointSaver
    ):
        self.config = config
        self.nlu_provider = nlu_provider
        self.graph = graph
        self.checkpointer = checkpointer

        # Dependency injection for digression handling
        knowledge_base = KnowledgeBase(config)
        help_generator = HelpGenerator(config)
        self.digression_handler = DigressionHandler(
            knowledge_base,
            help_generator
        )
```

### Key Methods

#### process_message

Main entry point for message processing. Uses LangGraph's checkpointing for automatic conversation resumption:

```python
async def process_message(self, msg: str, user_id: str) -> str:
    """
    Process user message with automatic checkpoint resumption.

    Args:
        msg: User message text
        user_id: Unique user identifier (becomes thread_id)

    Returns:
        Assistant response text
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
            "conversation_state": ConversationState.IDLE,
            # ... other initial state
        }
        result = await self.graph.ainvoke(input_state, config=config)

    return result["last_response"]
```

#### Flow Stack Helpers

Simple list operations handled as helper methods:

```python
def _push_flow(
    self,
    state: DialogueState,
    flow_name: str,
    reason: str | None = None
):
    """
    Push new flow to stack, pausing current one.

    Simple list operation - no separate manager class needed.
    """
    if state.flow_stack:
        current = state.flow_stack[-1]
        current.flow_state = FlowState.PAUSED
        current.paused_at = time.time()
        current.context = reason

    new_flow = FlowContext(
        flow_name=flow_name,
        flow_state=FlowState.ACTIVE,
        current_step=None,
        collected_slots={},
        started_at=time.time(),
    )
    state.flow_stack.append(new_flow)
    state.current_flow = flow_name

def _pop_flow(
    self,
    state: DialogueState,
    result: FlowState = FlowState.COMPLETED
):
    """
    Pop current flow and resume previous one.

    Simple list operation - no separate manager class needed.
    """
    if not state.flow_stack:
        raise ValueError("Cannot pop empty flow stack")

    # Complete current flow
    current = state.flow_stack.pop()
    current.flow_state = result
    current.completed_at = time.time()

    # Archive completed flow
    state.metadata.setdefault("completed_flows", []).append(current)

    # Resume previous flow if exists
    if state.flow_stack:
        previous = state.flow_stack[-1]
        previous.flow_state = FlowState.ACTIVE
        state.current_flow = previous.flow_name
    else:
        state.current_flow = "none"

def _get_active_flow(self, state: DialogueState) -> FlowContext | None:
    """Get currently active flow (top of stack)"""
    return state.flow_stack[-1] if state.flow_stack else None

def _get_paused_flows(self, state: DialogueState) -> list[FlowContext]:
    """Get all paused flows"""
    return [f for f in state.flow_stack if f.flow_state == FlowState.PAUSED]
```

**Design Rationale**: These are straightforward list operations without complex domain logic, so they don't justify a separate class.

## NLU Provider

### Responsibility

Understand user intent, extract entities, detect digressions, and identify resume requests with context awareness.

### Interface

```python
from typing import Protocol
import dspy

class INLUProvider(Protocol):
    """Protocol for NLU providers"""

    async def understand(
        self,
        user_message: str,
        history: dspy.History,
        context: DialogueContext
    ) -> NLUOutput:
        """
        Understand user message with structured types.

        Args:
            user_message: User's current message
            history: Conversation history (dspy.History)
            context: Dialogue context (DialogueContext)

        Returns:
            NLUOutput with structured slot values and metadata
        """
        ...
```

### Implementation (SoniDU)

DSPy-based implementation with automatic optimization and structured types:

```python
import dspy

class SoniDU(dspy.Module, INLUProvider):
    """
    Soni Dialogue Understanding module with structured types.

    Unified NLU that handles:
    - Slot value extraction
    - Intent detection and changes
    - Context-aware understanding with dspy.History
    """

    def __init__(self, cache_size: int = 1000, cache_ttl: int = 300) -> None:
        """Initialize SoniDU module."""
        super().__init__()
        self.predictor = dspy.ChainOfThought(DialogueUnderstanding)

        from cachetools import TTLCache
        self.nlu_cache: TTLCache[str, NLUOutput] = TTLCache(
            maxsize=cache_size,
            ttl=cache_ttl
        )

    async def understand(
        self,
        user_message: str,
        history: dspy.History,
        context: DialogueContext
    ) -> NLUOutput:
        """Understand user message with structured types.

        Args:
            user_message: User's current message
            history: Conversation history (dspy.History)
            context: Dialogue context (DialogueContext)

        Returns:
            NLUOutput with structured slot values and metadata
        """
        from datetime import datetime

        # Check cache
        cache_key = self._get_cache_key(user_message, history, context)
        if cache_key in self.nlu_cache:
            return self.nlu_cache[cache_key]

        # Call NLU with structured types
        current_datetime = datetime.now().isoformat()
        prediction = await self.predictor.acall(
            user_message=user_message,
            history=history,
            context=context,
            current_datetime=current_datetime
        )

        # Extract structured result (no parsing needed!)
        result: NLUOutput = prediction.result

        # Cache and return
        self.nlu_cache[cache_key] = result
        return result

    def _get_cache_key(
        self,
        user_message: str,
        history: dspy.History,
        context: DialogueContext
    ) -> str:
        """Generate cache key from structured inputs."""
        from soni.utils.hashing import generate_cache_key_from_dict

        return generate_cache_key_from_dict({
            "message": user_message,
            "history_length": len(history.messages),
            "context": context.model_dump()
        })
```

### NLU Result Structure

```python
from pydantic import BaseModel, Field
from enum import Enum
from typing import Any

class MessageType(str, Enum):
    """Type of user message."""
    SLOT_VALUE = "slot_value"
    INTENT_CHANGE = "intent_change"
    QUESTION = "question"
    CONFIRMATION = "confirmation"
    CONTINUE = "continue"

class SlotValue(BaseModel):
    """Extracted slot value with metadata."""
    name: str = Field(description="Slot name (must match expected_slots)")
    value: Any = Field(description="Extracted value")
    confidence: float = Field(ge=0.0, le=1.0, description="Extraction confidence")

class NLUOutput(BaseModel):
    """Complete NLU analysis result with structured types."""

    message_type: MessageType = Field(description="Type of user message")
    """Type of user message"""

    command: str = Field(description="User's intent/command")
    """User's intent or command"""

    slots: list[SlotValue] = Field(default_factory=list, description="Extracted slot values")
    """Extracted slot values with metadata"""

    confidence: float = Field(ge=0.0, le=1.0, description="Overall confidence")
    """Overall confidence (0.0 to 1.0)"""

    reasoning: str = Field(description="Step-by-step reasoning")
    """Step-by-step reasoning explaining the classification"""
```

## DigressionHandler

### Responsibility

Coordinate digression handling by delegating to specialized components based on digression type.

### Architecture

Coordinator pattern with focused sub-components:

```python
class DigressionHandler:
    """
    Coordinator for digression handling.

    Delegates to specialized components:
    - KnowledgeBase for questions
    - HelpGenerator for help and clarifications
    """

    def __init__(
        self,
        knowledge_base: KnowledgeBase,
        help_generator: HelpGenerator
    ):
        self.knowledge_base = knowledge_base
        self.help_generator = help_generator

    async def handle(
        self,
        state: DialogueState,
        digression_type: DigressionType,
        digression_topic: str
    ) -> DialogueState:
        """
        Coordinate digression handling.

        Delegates to appropriate component based on type,
        then returns control to main flow.
        """
        if digression_type == DigressionType.QUESTION:
            response = await self.knowledge_base.answer_question(
                digression_topic,
                state
            )

        elif digression_type in (DigressionType.CLARIFICATION, DigressionType.HELP):
            response = await self.help_generator.generate_help(state)

        elif digression_type == DigressionType.STATUS:
            response = await self.help_generator.generate_status(state)

        else:
            response = "I'm not sure how to help with that."

        # Increment digression depth
        state.digression_depth += 1
        state.last_digression_type = digression_type.value

        # Add response and re-prompt original question
        state.messages.append({
            "role": "assistant",
            "content": response
        })

        # Generate re-prompt
        reprompt = self._generate_reprompt(state)
        state.last_response = f"{response}\n\n{reprompt}"

        return state
```

### Design Rationale

Decomposed architecture following Single Responsibility Principle:
- **DigressionHandler**: Coordination only
- **KnowledgeBase**: Domain knowledge and question answering
- **HelpGenerator**: Contextual help generation

This separation enables:
- Easy testing of each component in isolation
- Extensibility (add RAG, vector DB, etc.)
- Clear responsibilities without God Objects

## KnowledgeBase

### Responsibility

Answer domain-specific questions using knowledge base, RAG, or documentation.

### Interface

```python
class KnowledgeBase:
    """
    Answers domain-specific questions.

    Can be extended with:
    - Vector database for semantic search
    - RAG pipeline for contextual answers
    - FAQ database
    - Documentation search
    """

    def __init__(self, config: SoniConfig):
        self.config = config
        self.faq = self._load_faq()

    async def answer_question(
        self,
        topic: str,
        context: DialogueState
    ) -> str:
        """
        Answer a domain-specific question.

        Args:
            topic: What the question is about
            context: Current conversation state

        Returns:
            Answer text
        """
        # Check FAQ first
        if answer := self._search_faq(topic):
            return answer

        # Fall back to LLM with context
        return await self._generate_answer(topic, context)
```

### Extension Points

```python
# Example: Add vector database
from chromadb import AsyncClient

class EnhancedKnowledgeBase(KnowledgeBase):
    def __init__(self, config: SoniConfig, vector_db: AsyncClient):
        super().__init__(config)
        self.vector_db = vector_db

    async def answer_question(self, topic: str, context: DialogueState) -> str:
        # Semantic search in vector database
        results = await self.vector_db.query(
            query_texts=[topic],
            n_results=3
        )

        if results:
            return await self._generate_answer_with_context(
                topic,
                context,
                retrieved_docs=results
            )

        return await super().answer_question(topic, context)
```

## HelpGenerator

### Responsibility

Generate contextual help and clarifications based on conversation state.

### Implementation

```python
class HelpGenerator:
    """
    Generates contextual help and clarifications.

    Provides:
    - General help about system capabilities
    - Status updates (what's been collected)
    - Clarifications (why information is needed)
    """

    def __init__(self, config: SoniConfig):
        self.config = config

    async def generate_help(self, state: DialogueState) -> str:
        """
        Generate contextual help message.

        Tailors help to current flow and collected information.
        """
        active_flow = self._get_active_flow(state)

        if active_flow:
            flow_config = self.config.flows[active_flow.flow_name]
            return f"""
I can help you {flow_config.description}.

So far you've provided:
{self._format_collected_slots(active_flow.collected_slots)}

I still need:
{self._format_missing_slots(active_flow, flow_config)}
"""

        return """
I can help you with:
{self._format_available_flows(self.config.flows)}
"""

    async def generate_status(self, state: DialogueState) -> str:
        """Generate status message showing progress"""
        active_flow = self._get_active_flow(state)

        if not active_flow:
            return "We're not currently working on anything."

        flow_config = self.config.flows[active_flow.flow_name]
        collected = len(active_flow.collected_slots)
        total = len(flow_config.slots)

        return f"""
We're working on: {flow_config.description}
Progress: {collected}/{total} information collected
"""

    async def generate_clarification(
        self,
        topic: str,
        state: DialogueState
    ) -> str:
        """Explain why certain information is needed"""
        # Implementation for explaining requirements
        pass
```

## Action Registry

### Responsibility

Register and execute external actions (API calls, database queries, etc.).

### Usage

```python
from soni.actions import ActionRegistry

@ActionRegistry.register("search_flights")
async def search_flights(
    origin: str,
    destination: str,
    date: str
) -> dict[str, Any]:
    """
    Search for available flights.

    Args:
        origin: Departure city
        destination: Arrival city
        date: Departure date (ISO format)

    Returns:
        Dictionary with 'flights' and 'cheapest_price'
    """
    response = await http_client.get(
        f"https://api.example.com/flights",
        params={"from": origin, "to": destination, "date": date}
    )

    flights = response.json()["data"]
    cheapest = min(f["price"] for f in flights)

    return {
        "flights": flights,
        "cheapest_price": cheapest
    }
```

### Interface

```python
class IActionHandler(Protocol):
    """Protocol for action handlers"""

    async def execute(
        self,
        action: str,
        inputs: dict[str, Any]
    ) -> dict[str, Any]:
        """Execute action with provided inputs"""
        ...
```

## Validator Registry

### Responsibility

Register and execute validation logic for slot values.

### Usage

```python
from soni.validation import ValidatorRegistry

@ValidatorRegistry.register("future_date_only")
def validate_future_date(value: str) -> bool:
    """
    Validate that date is in the future.

    Args:
        value: Date string in ISO format

    Returns:
        True if date is in future, False otherwise
    """
    try:
        date = datetime.fromisoformat(value)
        return date > datetime.now()
    except ValueError:
        return False

@ValidatorRegistry.register("valid_airport_city")
async def validate_airport_city(value: str) -> bool:
    """
    Validate that city has an airport.

    Can be async for database/API checks.
    """
    valid_cities = await get_cities_with_airports()
    return value.lower() in [c.lower() for c in valid_cities]
```

## Checkpointer

### Responsibility

Async persistence for dialogue state using various backends.

### Backends

**SQLite** (development):
```python
from langgraph.checkpoint.sqlite import SqliteSaver

checkpointer = SqliteSaver.from_conn_string("dialogue_state.db")
```

**PostgreSQL** (production):
```python
from langgraph.checkpoint.postgres import PostgresSaver

checkpointer = PostgresSaver.from_conn_string(
    "postgresql://user:pass@localhost/soni"
)
```

**Redis** (high-performance):
```python
from langgraph.checkpoint.redis import RedisSaver

checkpointer = RedisSaver.from_client(redis_client)
```

### Usage

Checkpointer is passed to LangGraph during compilation:

```python
graph = builder.compile(checkpointer=checkpointer)
```

LangGraph automatically:
- Saves state after each node execution
- Isolates conversations by `thread_id`
- Enables resumption via `aget_state()` and `Command(resume=)`

## Component Interactions

### Message Processing

```
User Message
  ↓
RuntimeLoop.process_message()
  ├─ Calls: graph.aget_state() / graph.ainvoke()
  └─ Uses: checkpointer (automatic via LangGraph)
  ↓
Understand Node
  ├─ Calls: nlu_provider.predict()
  └─ Returns: NLUResult
  ↓
Conditional Routing (based on NLU result)
  ├─ If digression → digression_handler.handle()
  │   ├─ Calls: knowledge_base.answer_question()
  │   └─ Calls: help_generator.generate_help()
  ├─ If intent change → RuntimeLoop._push_flow()
  └─ If slot value → Validate → Continue
  ↓
Action Execution (if needed)
  └─ Calls: ActionRegistry.execute()
  ↓
Response Generation
  └─ Returns to user
```

### Dependency Injection

```python
# Create dependencies
config = load_config("soni.yaml")
nlu_provider = SoniDU()
checkpointer = SqliteSaver.from_conn_string("state.db")

# Build graph
graph_builder = GraphBuilder(config)
graph = graph_builder.build()
compiled_graph = graph.compile(checkpointer=checkpointer)

# Create RuntimeLoop with dependencies
runtime = RuntimeLoop(
    config=config,
    nlu_provider=nlu_provider,
    graph=compiled_graph,
    checkpointer=checkpointer
)

# Use
response = await runtime.process_message("Book a flight", user_id="user123")
```

## Summary

Soni's component architecture follows these principles:

1. **Single Responsibility**: Each component has one clear purpose
2. **Dependency Injection**: Components receive dependencies via constructors
3. **Interface-Based**: Use Protocols for loose coupling
4. **Async-First**: All I/O operations are async
5. **No God Objects**: Complex logic delegated to specialized components
6. **Simple Operations**: Helper methods for straightforward operations

This design enables:
- Easy testing with mocks
- Extensibility (swap implementations)
- Clear ownership (who does what)
- Maintainability (focused components)

## Next Steps

- **[04-state-machine.md](04-state-machine.md)** - DialogueState schema and transitions
- **[05-message-flow.md](05-message-flow.md)** - Message processing pipeline
- **[06-nlu-system.md](06-nlu-system.md)** - Complete NLU architecture including:
  - Structured Pydantic types (NLUOutput, DialogueContext, SlotValue)
  - dspy.History for conversation management
  - DummyLM for testing patterns
  - Production best practices (error handling, logging, monitoring)
- **[08-langgraph-integration.md](08-langgraph-integration.md)** - LangGraph patterns

---

**Design Version**: v0.8 (Production-Ready with Structured Types)
**Status**: Production-ready design specification
