## Task: 001 - Core Types (TypedDicts)

**ID de tarea:** 001
**Hito:** 1 - Core Foundations
**Dependencias:** 000
**Duración estimada:** 4 horas

### Objetivo

Implement the core TypedDict structures for state management: `DialogueState`, `FlowContext`, and `RuntimeContext`.

### Contexto

These TypedDicts are the foundation of all state management in Soni. They must be pure data structures with no methods, following LangGraph's state management requirements.

### Entregables

- [ ] `core/types.py` with DialogueState TypedDict
- [ ] `core/types.py` with FlowContext TypedDict
- [ ] `core/types.py` with RuntimeContext TypedDict
- [ ] Unit tests for type creation and serialization
- [ ] 100% test coverage for this module

### Implementación Detallada

#### Paso 1: Create core/types.py

**Archivo:** `src/soni/core/types.py`

```python
"""Core type definitions for Soni v3.0.

Pure TypedDict structures for LangGraph state management.
No methods - these are data-only structures.
Uses Annotated reducers for message aggregation.
"""
from typing import Any, Annotated, Literal, TypedDict
from langgraph.graph.message import add_messages
from langchain_core.messages import AnyMessage


FlowState = Literal["idle", "active", "waiting_input", "done", "error"]


class FlowContext(TypedDict):
    """Context for a single flow instance on the stack."""
    
    flow_id: str  # Unique instance ID (UUID)
    flow_name: str  # Flow definition name
    flow_state: Literal["active", "completed", "cancelled"]
    current_step: str | None  # Current step name
    step_index: int  # Current step index
    outputs: dict[str, Any]  # Flow outputs
    started_at: float  # Timestamp


class DialogueState(TypedDict):
    """Complete dialogue state for LangGraph.
    
    This is the single source of truth for conversation state.
    All nodes read from and write to this structure.
    
    Uses Annotated reducers:
    - messages: Uses add_messages for proper message aggregation
    """
    
    # User communication (with reducer for message accumulation)
    user_message: str
    last_response: str
    messages: Annotated[list[AnyMessage], add_messages]  # Reducer for messages
    
    # Flow management
    flow_stack: list[FlowContext]
    flow_slots: dict[str, dict[str, Any]]  # flow_id -> slot_name -> value
    
    # State tracking
    flow_state: FlowState
    waiting_for_slot: str | None
    
    # Commands from NLU (replaced each turn, no reducer)
    commands: list[dict[str, Any]]  # Serialized commands
    
    # Transient data
    response: str | None
    action_result: dict[str, Any] | None
    
    # Metadata
    turn_count: int
    metadata: dict[str, Any]


class RuntimeContext(TypedDict):
    """Runtime context with injected dependencies.
    
    Passed to nodes via LangGraph's configurable pattern.
    """
    
    config: Any  # SoniConfig
    flow_manager: Any  # FlowManager
    action_handler: Any  # ActionHandler
    du: Any  # NLU provider


def create_empty_dialogue_state() -> DialogueState:
    """Factory function for empty dialogue state."""
    return {
        "user_message": "",
        "last_response": "",
        "messages": [],
        "flow_stack": [],
        "flow_slots": {},
        "flow_state": "idle",
        "waiting_for_slot": None,
        "commands": [],
        "response": None,
        "action_result": None,
        "turn_count": 0,
        "metadata": {},
    }
```

### TDD Cycle (MANDATORY for new features)

#### Red Phase: Write Failing Tests

**Test file:** `tests/unit/core/test_types.py`

```python
"""Unit tests for core types."""
import pytest
from soni.core.types import (
    DialogueState,
    FlowContext,
    create_empty_dialogue_state,
)


class TestDialogueState:
    """Tests for DialogueState TypedDict."""

    def test_create_empty_dialogue_state_returns_valid_structure(self):
        """
        GIVEN nothing
        WHEN create_empty_dialogue_state is called
        THEN returns a valid DialogueState with all required keys
        """
        # Act
        state = create_empty_dialogue_state()
        
        # Assert
        assert state["flow_stack"] == []
        assert state["flow_slots"] == {}
        assert state["flow_state"] == "idle"
        assert state["turn_count"] == 0

    def test_dialogue_state_is_json_serializable(self):
        """
        GIVEN a DialogueState
        WHEN serialized to JSON
        THEN no errors occur and can be deserialized
        """
        import json
        
        # Arrange
        state = create_empty_dialogue_state()
        
        # Act
        json_str = json.dumps(state)
        restored = json.loads(json_str)
        
        # Assert
        assert restored == state


class TestFlowContext:
    """Tests for FlowContext TypedDict."""

    def test_flow_context_has_required_fields(self):
        """
        GIVEN a FlowContext dict
        WHEN created with all required fields
        THEN can be accessed without KeyError
        """
        # Arrange
        context: FlowContext = {
            "flow_id": "test-123",
            "flow_name": "book_flight",
            "flow_state": "active",
            "current_step": None,
            "step_index": 0,
            "outputs": {},
            "started_at": 0.0,
        }
        
        # Assert
        assert context["flow_id"] == "test-123"
        assert context["flow_state"] == "active"
```

**Verify tests fail:**
```bash
uv run pytest tests/unit/core/test_types.py -v
# Expected: FAILED (module not implemented yet)
```

#### Green Phase: Make Tests Pass

Implement `core/types.py` as shown above.

```bash
uv run pytest tests/unit/core/test_types.py -v
# Expected: PASSED ✅
```

### Criterios de Éxito

- [ ] `DialogueState` TypedDict exists with all fields
- [ ] `FlowContext` TypedDict exists with all fields
- [ ] `create_empty_dialogue_state()` returns valid state
- [ ] All types are JSON serializable
- [ ] Tests pass: `pytest tests/unit/core/test_types.py -v`
- [ ] Type checking passes: `mypy src/soni/core/types.py`

### Validación Manual

```bash
uv run python -c "from soni.core.types import create_empty_dialogue_state; print(create_empty_dialogue_state())"
```

### Referencias

- `archive/src/soni/core/types.py` - Reference implementation
- LangGraph state management docs
