# Phase 4: LangGraph Integration & Dialogue Management

**Goal**: Complete dialogue management with LangGraph nodes, routing, and graph construction.

**Duration**: 3-4 days

**Dependencies**: Phase 1-3 (Foundation, State, NLU)

## Overview

This phase implements the dialogue management layer using LangGraph:
- Node implementations (understand, validate, collect, etc.)
- Routing functions
- Graph builder
- RuntimeContext injection
- End-to-end flow execution

## Tasks

### Task 4.1: Understand Node

**Status**: 📋 Backlog

**File**: `src/soni/dm/nodes/understand.py`

**What**: Implement understand node that calls NLU.

**Why**: Entry point for all user messages (see `docs/design/05-message-flow.md`).

**Implementation**:

```python
from soni.core.types import DialogueState, RuntimeContext
from langgraph.runtime import Runtime
import time

async def understand_node(
    state: DialogueState,
    runtime: Runtime[RuntimeContext]
) -> dict:
    """
    Understand user message via NLU.

    Pattern: With Dependencies (uses context_schema)

    Args:
        state: Current dialogue state
        runtime: Runtime context with dependencies

    Returns:
        Partial state updates with NLU result
    """
    # Access dependencies (type-safe)
    nlu_provider = runtime.context["nlu_provider"]
    flow_manager = runtime.context["flow_manager"]

    # Build NLU context
    active_ctx = flow_manager.get_active_context(state)
    current_flow_name = active_ctx["flow_name"] if active_ctx else "none"

    scope_manager = runtime.context["scope_manager"]

    dialogue_context = {
        "current_slots": state["flow_slots"].get(active_ctx["flow_id"], {}) if active_ctx else {},
        "available_actions": scope_manager.get_available_actions(state),
        "available_flows": scope_manager.get_available_flows(state),
        "current_flow": current_flow_name,
        "expected_slots": [],  # TODO: Get from flow definition
        "history": state["messages"][-5:] if state["messages"] else []  # Last 5 messages
    }

    # Call NLU
    nlu_result = await nlu_provider.understand(
        state["user_message"],
        dialogue_context
    )

    return {
        "nlu_result": nlu_result,
        "conversation_state": "understanding",
        "last_nlu_call": time.time()
    }
```

**Tests**:

`tests/unit/test_nodes.py`:
```python
import pytest
from unittest.mock import AsyncMock, MagicMock
from soni.dm.nodes.understand import understand_node
from soni.core.state import create_initial_state

@pytest.mark.asyncio
async def test_understand_node():
    """Test understand node calls NLU."""
    # Arrange
    state = create_initial_state("Hello")

    # Mock runtime context
    mock_nlu = AsyncMock()
    mock_nlu.understand.return_value = {
        "message_type": "interruption",
        "command": "greet",
        "slots": [],
        "confidence": 0.9,
        "reasoning": "greeting"
    }

    mock_flow_manager = MagicMock()
    mock_flow_manager.get_active_context.return_value = None

    mock_scope_manager = MagicMock()
    mock_scope_manager.get_available_actions.return_value = ["greet"]
    mock_scope_manager.get_available_flows.return_value = []

    mock_runtime = MagicMock()
    mock_runtime.context = {
        "nlu_provider": mock_nlu,
        "flow_manager": mock_flow_manager,
        "scope_manager": mock_scope_manager
    }

    # Act
    result = await understand_node(state, mock_runtime)

    # Assert
    assert result["conversation_state"] == "understanding"
    assert result["nlu_result"]["command"] == "greet"
    mock_nlu.understand.assert_called_once()
```

**Completion Criteria**:
- [ ] Node implemented
- [ ] NLU integration working
- [ ] Tests passing
- [ ] Mypy passes

---

### Task 4.2: Routing Functions

**Status**: 📋 Backlog

**File**: `src/soni/dm/routing.py`

**What**: Implement routing functions for conditional edges.

**Why**: Determine next node based on NLU result.

**Implementation**:

```python
from soni.core.types import DialogueState

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

    if not nlu_result:
        return "generate_response"

    message_type = nlu_result.get("message_type")

    # Route based on message type
    match message_type:
        case "slot_value":
            return "validate_slot"
        case "correction":
            return "handle_correction"
        case "modification":
            return "handle_modification"
        case "interruption":
            return "handle_interruption"
        case "digression":
            return "handle_digression"
        case "clarification":
            return "handle_clarification"
        case "cancellation":
            return "handle_cancellation"
        case "confirmation":
            return "handle_confirmation"
        case "continuation":
            return "continue_flow"
        case _:
            return "generate_response"

def route_after_validate(state: DialogueState) -> str:
    """
    Route after slot validation.

    Args:
        state: Current dialogue state

    Returns:
        Next node name
    """
    # Check if all required slots filled
    active_flow = state["flow_stack"][-1] if state["flow_stack"] else None

    if not active_flow:
        return "generate_response"

    # TODO: Check slot requirements from flow definition
    # For now, simple logic
    if state.get("all_slots_filled"):
        return "execute_action"
    else:
        return "collect_next_slot"
```

**Tests**:

`tests/unit/test_routing.py`:
```python
def test_route_after_understand_slot_value():
    """Test routing with slot_value message type."""
    # Arrange
    state = create_empty_state()
    state["nlu_result"] = {
        "message_type": "slot_value",
        "command": "book_flight",
        "slots": [{"name": "origin", "value": "Madrid"}]
    }

    # Act
    next_node = route_after_understand(state)

    # Assert
    assert next_node == "validate_slot"

def test_route_after_understand_interruption():
    """Test routing with interruption message type."""
    # Arrange
    state = create_empty_state()
    state["nlu_result"] = {
        "message_type": "interruption",
        "command": "book_flight"
    }

    # Act
    next_node = route_after_understand(state)

    # Assert
    assert next_node == "handle_interruption"
```

**Completion Criteria**:
- [ ] Routing functions implemented
- [ ] All message types handled
- [ ] Tests passing

---

### Task 4.3: Additional Nodes

**Status**: 📋 Backlog

**Files**: `src/soni/dm/nodes/*.py`

**What**: Implement remaining core nodes.

**Why**: Complete the dialogue management pipeline.

**Nodes to Implement**:

1. **`validate_slot.py`**: Validate and normalize slot value
2. **`collect_next_slot.py`**: Ask for next required slot (uses `interrupt()`)
3. **`handle_intent_change.py`**: Start new flow
4. **`handle_digression.py`**: Handle questions without flow changes
5. **`execute_action.py`**: Execute action via ActionHandler
6. **`generate_response.py`**: Generate final response

**Example - collect_next_slot.py**:

```python
from soni.core.types import DialogueState, RuntimeContext
from langgraph.runtime import Runtime
from langgraph.types import interrupt

async def collect_next_slot_node(
    state: DialogueState,
    runtime: Runtime[RuntimeContext]
) -> dict:
    """
    Ask for next required slot and pause execution.

    Uses interrupt() to wait for user response.

    Args:
        state: Current dialogue state
        runtime: Runtime context

    Returns:
        Partial state updates
    """
    # Get active flow (idempotent operation - safe before interrupt)
    flow_manager = runtime.context["flow_manager"]
    active_ctx = flow_manager.get_active_context(state)

    if not active_ctx:
        return {"conversation_state": "idle"}

    # Determine next slot to collect
    # TODO: Get from flow definition
    next_slot = "origin"  # Placeholder

    # Generate prompt
    prompt = f"Please provide your {next_slot}."

    # Pause here - wait for user response
    user_response = interrupt({
        "type": "slot_request",
        "slot": next_slot,
        "prompt": prompt
    })

    # Code after interrupt() executes when user responds
    return {
        "user_message": user_response,
        "waiting_for_slot": next_slot,
        "conversation_state": "waiting_for_slot",
        "last_response": prompt
    }
```

**Completion Criteria**:
- [ ] All 6 nodes implemented
- [ ] Interrupt pattern working
- [ ] Tests for each node
- [ ] Mypy passes

---

### Task 4.4: Graph Builder

**Status**: 📋 Backlog

**File**: `src/soni/dm/builder.py`

**What**: Build LangGraph from configuration.

**Why**: Assemble all nodes into executable graph.

**Implementation**:

```python
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import InMemorySaver
from soni.core.types import DialogueState, RuntimeContext
from soni.dm.nodes.understand import understand_node
from soni.dm.nodes.validate_slot import validate_slot_node
from soni.dm.nodes.collect_next_slot import collect_next_slot_node
from soni.dm.nodes.handle_intent_change import handle_intent_change_node
from soni.dm.nodes.handle_digression import handle_digression_node
from soni.dm.nodes.execute_action import execute_action_node
from soni.dm.nodes.generate_response import generate_response_node
from soni.dm.routing import route_after_understand, route_after_validate

def build_graph(
    context: RuntimeContext,
    checkpointer = None
):
    """
    Build LangGraph from Soni configuration.

    Args:
        context: Runtime context with dependencies
        checkpointer: Optional checkpointer (defaults to InMemorySaver)

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
    builder.add_node("collect_next_slot", collect_next_slot_node)
    builder.add_node("handle_intent_change", handle_intent_change_node)
    builder.add_node("handle_digression", handle_digression_node)
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

    # After intent change, back to understand
    builder.add_edge("handle_intent_change", "understand")

    # Action → response → END
    builder.add_edge("execute_action", "generate_response")
    builder.add_edge("generate_response", END)

    # Compile with checkpointer
    if checkpointer is None:
        checkpointer = InMemorySaver()

    return builder.compile(checkpointer=checkpointer)
```

**Tests**:

`tests/integration/test_graph_builder.py`:
```python
import pytest
from soni.dm.builder import build_graph
from soni.core.state import create_initial_state
from unittest.mock import AsyncMock, MagicMock

@pytest.mark.asyncio
async def test_graph_construction():
    """Test graph builds without errors."""
    # Arrange
    mock_context = {
        "flow_manager": MagicMock(),
        "nlu_provider": AsyncMock(),
        "action_handler": AsyncMock(),
        "scope_manager": MagicMock(),
        "normalizer": AsyncMock()
    }

    # Act
    graph = build_graph(mock_context)

    # Assert
    assert graph is not None
    # Graph should have nodes
    assert len(graph.nodes) > 0
```

**Completion Criteria**:
- [ ] Builder implemented
- [ ] All nodes connected
- [ ] Routing edges configured
- [ ] Tests passing

---

### Task 4.5: End-to-End Flow Test

**Status**: 📋 Backlog

**File**: `tests/integration/test_dialogue_flow.py`

**What**: Test complete dialogue flow end-to-end.

**Why**: Verify all components work together.

**Implementation**:

```python
import pytest
import dspy
from dspy.utils.dummies import DummyLM
from langgraph.types import Command
from soni.dm.builder import build_graph
from soni.du.modules import SoniDU
from soni.flow.manager import FlowManager
from soni.core.state import create_initial_state
from unittest.mock import MagicMock, AsyncMock

@pytest.mark.asyncio
async def test_complete_dialogue_flow():
    """Test complete booking flow with interrupts and resumption."""
    # Arrange - Set up DummyLM
    lm = DummyLM([
        # First call: Intent detection
        {
            "result": {
                "message_type": "interruption",
                "command": "book_flight",
                "slots": [],
                "confidence": 0.95,
                "reasoning": "Booking intent"
            }
        },
        # Second call: Slot extraction
        {
            "result": {
                "message_type": "slot_value",
                "command": "book_flight",
                "slots": [
                    {"name": "origin", "value": "Madrid", "confidence": 0.9}
                ],
                "confidence": 0.9,
                "reasoning": "Origin provided"
            }
        }
    ])
    dspy.configure(lm=lm)

    # Create dependencies
    nlu_module = SoniDU()
    nlu_provider = nlu_module  # SoniDU implements INLUProvider directly
    flow_manager = FlowManager()

    mock_action_handler = AsyncMock()
    mock_action_handler.execute.return_value = {"booking_ref": "BK-123"}

    mock_scope_manager = MagicMock()
    mock_scope_manager.get_available_actions.return_value = ["book_flight"]
    mock_scope_manager.get_available_flows.return_value = ["book_flight"]

    mock_normalizer = AsyncMock()
    mock_normalizer.normalize.return_value = "Madrid"

    context = {
        "flow_manager": flow_manager,
        "nlu_provider": nlu_provider,
        "action_handler": mock_action_handler,
        "scope_manager": mock_scope_manager,
        "normalizer": mock_normalizer
    }

    # Build graph
    graph = build_graph(context)

    # Act - Step 1: User starts booking
    state = create_initial_state("I want to book a flight")
    config = {"configurable": {"thread_id": "test-user-1"}}

    result = await graph.ainvoke(state, config=config, context=context)

    # Assert - Should have started flow and be waiting for slot
    snapshot = await graph.aget_state(config)
    assert snapshot.next  # Should be interrupted

    # Act - Step 2: User provides origin
    result = await graph.ainvoke(
        Command(resume="Madrid"),
        config=config,
        context=context
    )

    # Assert - Flow should continue
    final_state = result
    assert "Madrid" in str(final_state)  # Origin should be collected
```

**Completion Criteria**:
- [ ] End-to-end test implemented
- [ ] Interrupt/resume working
- [ ] Multiple turns tested
- [ ] Test passing

---

## Phase 4 Completion Checklist

Before proceeding to Phase 5, verify:

- [ ] All Task 4.x completed
- [ ] All nodes implemented
- [ ] Graph builds successfully
- [ ] End-to-end test passing
- [ ] Interrupt/resume working
- [ ] Mypy passes
- [ ] Code committed

## Phase 4 Validation

```bash
# Type checking
uv run mypy src/soni/dm

# Unit tests
uv run pytest tests/unit/test_nodes.py -v
uv run pytest tests/unit/test_routing.py -v

# Integration tests
uv run pytest tests/integration/test_graph_builder.py -v
uv run pytest tests/integration/test_dialogue_flow.py -v

# Coverage
uv run pytest tests/ --cov=soni.dm --cov-report=term-missing
```

## Next Steps

Once Phase 4 is complete:

1. Verify end-to-end flows work
2. Test with real LLM (optional)
3. Proceed to **[05-phase-5-production.md](05-phase-5-production.md)**

---

**Phase**: 4 of 5
**Status**: 📋 Backlog
**Estimated Duration**: 3-4 days
