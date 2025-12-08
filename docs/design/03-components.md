# Soni Framework - Components

## Overview

Soni's architecture is built around focused, single-responsibility components that work together to enable sophisticated conversational AI. This document details each component's responsibilities, interfaces, and implementation patterns following SOLID principles.

## RuntimeLoop

### Responsibility

Main orchestrator for conversation management. Coordinates message processing and delegation to specialized components.

### Design Philosophy

RuntimeLoop is an **orchestrator**, not a God Object:
- **Flow management** → Delegated to `FlowManager`
- **Complex domain logic** (digressions, knowledge retrieval) → Delegated to specialized components
- **Orchestration only** → RuntimeLoop coordinates without implementing business logic

### Architecture

```python
class RuntimeLoop:
    """
    Main orchestrator for conversation management.

    Delegates all business logic to specialized components.
    """

    def __init__(
        self,
        config: SoniConfig,
        nlu_provider: INLUProvider,
        flow_manager: FlowManager,
        graph: CompiledGraph,
        checkpointer: BaseCheckpointSaver
    ):
        self.config = config
        self.nlu_provider = nlu_provider
        self.flow_manager = flow_manager  # Injected dependency
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
        input_state = create_initial_state()
        input_state["user_message"] = msg
        result = await self.graph.ainvoke(input_state, config=config)

    return result["last_response"]
```

## FlowManager (SRP)

### Responsibility

Manages the flow execution stack and data heap. Encapsulates all flow state manipulation logic.

### Interface

```python
class FlowManager:
    """
    Manages flow stack and flow-scoped data.

    Responsibilities:
    - Push/Pop flow instances
    - Data access (get/set slots)
    - Stack depth enforcement
    - Memory pruning
    """

    def __init__(self, config: SoniConfig):
        """Initialize with configuration."""
        self.config = config

    def push_flow(
        self,
        state: DialogueState,
        flow_name: str,
        inputs: dict[str, Any] | None = None,
        reason: str | None = None
    ) -> str:
        """Start a new flow instance. Returns flow_id."""
        ...

    def pop_flow(
        self,
        state: DialogueState,
        outputs: dict[str, Any] | None = None,
        result: FlowState = "completed"
    ) -> None:
        """Finish current flow instance."""
        ...

    def get_active_context(self, state: DialogueState) -> FlowContext | None:
        """Get currently active flow context."""
        ...

    def get_slot(self, state: DialogueState, slot_name: str) -> Any:
        """Get slot value from active flow."""
        ...

    def set_slot(self, state: DialogueState, slot_name: str, value: Any) -> None:
        """Set slot value in active flow."""
        ...
```

## FlowStepManager

### Responsibility

Manages flow step progression and tracking. Encapsulates all step-related logic including step completion checking, step advancement, and iterative advancement through completed steps.

### Design Philosophy

FlowStepManager follows **Single Responsibility Principle (SRP)** by focusing exclusively on step progression logic, separate from flow stack management (FlowManager) and orchestration (RuntimeLoop).

### Key Methods

#### advance_through_completed_steps

**Purpose**: Iteratively advance through all completed steps until finding an incomplete one.

**When to use**:
- After saving multiple slots in a single message
- When automatic advancement through completed steps is needed
- In `validate_slot_node` after processing slots
- In `handle_intent_change_node` after activating flow with slots

**Example**:
```python
# After saving multiple slots
updates = step_manager.advance_through_completed_steps(state, context)
state.update(updates)
```

**Behavior**:
1. Checks if current step is complete
2. If complete, advances to next step
3. Repeats until finding an incomplete step or flow completes
4. Returns state updates with `current_step`, `conversation_state`, `waiting_for_slot`, etc.

**Safety Limit**: Maximum 20 iterations to prevent infinite loops

**Implementation**:
```python
class FlowStepManager:
    """Manages flow step progression and tracking."""

    def advance_through_completed_steps(
        self,
        state: DialogueState,
        context: RuntimeContext,
    ) -> dict[str, Any]:
        """
        Advance through all completed steps until finding an incomplete one.

        Critical for handling cases where multiple slots are provided in one message.
        """
        max_iterations = 20  # Safety limit
        iterations = 0

        while iterations < max_iterations:
            iterations += 1
            current_step_config = self.get_current_step_config(state, context)

            if not current_step_config:
                return {"conversation_state": "completed"}

            is_complete = self.is_step_complete(state, current_step_config, context)

            if not is_complete:
                # Found incomplete step - stop here
                return {
                    "conversation_state": "waiting_for_slot",
                    "waiting_for_slot": current_step_config.slot,
                    # ...
                }

            # Advance to next step
            advance_updates = self.advance_to_next_step(state, context)
            if advance_updates.get("conversation_state") == "completed":
                return advance_updates

            state.update(advance_updates)

        # Safety: reached max iterations
        return {"conversation_state": "error"}
```

### Helper Functions in validate_slot_node

The `validate_slot_node` uses several helper functions to process multiple slots:

#### _process_all_slots

Processes and normalizes all slots from NLU result. Handles different slot formats (dict, SlotValue model, string).

**Signature**:
```python
async def _process_all_slots(
    slots: list,
    state: DialogueState,
    active_ctx: FlowContext,
    normalizer: INormalizer,
) -> dict[str, dict[str, Any]]:
    """Process and normalize all slots from NLU result."""
```

#### _detect_correction_or_modification

Detects if a message is a correction or modification based on `message_type` and slot actions.

**Signature**:
```python
def _detect_correction_or_modification(
    slots: list,
    message_type: str,
) -> bool:
    """Detect if message is a correction or modification."""
```

#### _handle_correction_flow

Handles correction/modification flow, restoring the correct step and updating state accordingly.

**Signature**:
```python
def _handle_correction_flow(
    state: DialogueState,
    runtime: Any,
    flow_slots: dict[str, dict[str, Any]],
    previous_step: str | None,
) -> dict[str, Any]:
    """Handle correction/modification flow."""
```

### Helper Functions in handle_intent_change_node

The `handle_intent_change_node` uses a helper function to extract slots from NLU results:

#### _extract_slots_from_nlu

Extracts slots from NLU result, handling different slot formats (dict, SlotValue model).

**Signature**:
```python
def _extract_slots_from_nlu(nlu_result: dict[str, Any]) -> dict[str, Any]:
    """Extract slots from NLU result."""
```

**Usage**: Called when a new flow is activated with slots in the initial message (e.g., "Book a flight from New York to Los Angeles").

### Usage Example

```python
# In a LangGraph node:
async def handle_intent_change_node(
    state: DialogueState,
    context: RuntimeContext
) -> dict[str, Any]:
    """Node that handles flow interruptions."""

    new_intent = state["nlu_result"]["command"]

    if new_intent == "cancel":
        # Cancel current flow
        context.flow_manager.pop_flow(state, result="cancelled")

        if state["flow_stack"]:
            return {"conversation_state": "understanding"}
        else:
            return {"conversation_state": "idle"}
    else:
        # Start new flow
        flow_id = context.flow_manager.push_flow(
            state,
            new_intent,
            inputs={},
            reason=f"User wants to {new_intent}"
        )
        return {"conversation_state": "waiting_for_slot"}
```

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
        """Understand user message with structured types."""
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

        IMPORTANT: Does NOT modify flow_stack.
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
        state["digression_depth"] += 1
        state["last_digression_type"] = digression_type.value

        # Add response and re-prompt original question
        state["messages"].append({
            "role": "assistant",
            "content": response
        })

        # Generate re-prompt
        reprompt = self._generate_reprompt(state)
        state["last_response"] = f"{response}\n\n{reprompt}"

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

## RuntimeContext (Dependency Injection)

### Responsibility

Container for injecting dependencies into LangGraph nodes.

### Structure

```python
@dataclass
class RuntimeContext:
    """
    Runtime context with injected dependencies.

    Passed to all LangGraph nodes for access to services.
    """

    config: SoniConfig
    flow_manager: FlowManager
    nlu_provider: INLUProvider
    action_handler: IActionHandler
    scope_manager: IScopeManager
    normalizer: INormalizer
```

### Usage in Nodes

```python
async def understand_node(
    state: DialogueState,
    context: RuntimeContext
) -> dict[str, Any]:
    """Node that performs NLU understanding."""

    # Get current flow from FlowManager
    active_context = context.flow_manager.get_active_context(state)
    current_flow_name = active_context["flow_name"] if active_context else "none"

    # Build NLU context
    dialogue_context = DialogueContext(
        current_slots=state["flow_slots"].get(active_context["flow_id"], {}) if active_context else {},
        available_actions=context.scope_manager.get_available_actions(state),
        available_flows=context.scope_manager.get_available_flows(state),
        current_flow=current_flow_name,
        expected_slots=get_expected_slots(state, context.config)
    )

    # Call NLU
    nlu_result: NLUOutput = await context.nlu_provider.understand(
        user_message=state["messages"][-1]["content"],
        history=build_history(state),
        context=dialogue_context
    )

    return {
        "nlu_result": nlu_result.model_dump(),
        "conversation_state": "understanding"
    }
```

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
  ├─ Calls: nlu_provider.understand()
  └─ Returns: NLUOutput
  ↓
Conditional Routing (based on NLU result)
  ├─ If digression → digression_handler.handle()
  │   ├─ Calls: knowledge_base.answer_question()
  │   └─ Calls: help_generator.generate_help()
  ├─ If intent change → flow_manager.push_flow()
  └─ If slot value → Validate → flow_manager.set_slot()
  ↓
Action Execution (if needed)
  └─ Calls: ActionRegistry.execute()
  ↓
Flow Completion
  └─ Calls: flow_manager.pop_flow()
  ↓
Response Generation
  └─ Returns to user
```

### Dependency Injection

```python
# Create dependencies
config = load_config("soni.yaml")
nlu_provider = SoniDU()
flow_manager = FlowManager(config)
checkpointer = SqliteSaver.from_conn_string("state.db")

# Build graph
graph_builder = GraphBuilder(config)
graph = graph_builder.build()
compiled_graph = graph.compile(checkpointer=checkpointer)

# Create RuntimeContext for nodes
runtime_context = RuntimeContext(
    config=config,
    flow_manager=flow_manager,
    nlu_provider=nlu_provider,
    action_handler=action_handler,
    scope_manager=scope_manager,
    normalizer=normalizer
)

# Create RuntimeLoop with dependencies
runtime = RuntimeLoop(
    config=config,
    nlu_provider=nlu_provider,
    flow_manager=flow_manager,
    graph=compiled_graph,
    checkpointer=checkpointer
)

# Use
response = await runtime.process_message("Book a flight", user_id="user123")
```

## Summary

Soni's component architecture follows these principles:

1. **Single Responsibility (SRP)**: Each component has one clear purpose
   - `FlowManager`: Flow stack operations
   - `RuntimeLoop`: Orchestration only
   - `DigressionHandler`: Digression coordination

2. **Dependency Injection**: Components receive dependencies via constructors
   - `RuntimeContext` passed to all nodes
   - Easy to test with mocks

3. **Interface-Based**: Use Protocols for loose coupling
   - `INLUProvider`, `IActionHandler`, etc.

4. **Async-First**: All I/O operations are async

5. **No God Objects**: Complex logic delegated to specialized components

This design enables:
- Easy testing with mocks
- Extensibility (swap implementations)
- Clear ownership (who does what)
- Maintainability (focused components)

## Next Steps

- **[04-state-machine.md](04-state-machine.md)** - DialogueState schema and transitions
- **[05-message-flow.md](05-message-flow.md)** - Message processing pipeline
- **[06-nlu-system.md](06-nlu-system.md)** - Complete NLU architecture
- **[07-flow-management.md](07-flow-management.md)** - Flow stack mechanics
- **[08-langgraph-integration.md](08-langgraph-integration.md)** - LangGraph patterns

---

**Design Version**: v1.0 (SOLID Compliant)
**Status**: Production-ready design specification
**Last Updated**: 2024-12-03
