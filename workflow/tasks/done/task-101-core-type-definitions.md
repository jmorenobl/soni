## Task: 1.1 - Core Type Definitions

**ID de tarea:** 101
**Hito:** Phase 1 - Core Foundation
**Dependencias:** Ninguna
**Duración estimada:** 2-3 horas

### Objetivo

Define all TypedDict structures for state management that will be used throughout the framework. These types are required by LangGraph and provide runtime type safety.

### Contexto

This is the foundational task for Phase 1. TypedDict structures are required by LangGraph for state management and provide runtime type safety. All other components will depend on these type definitions.

**Reference:** [docs/implementation/01-phase-1-foundation.md](../../docs/implementation/01-phase-1-foundation.md) - Task 1.1

### Entregables

- [ ] All TypedDict classes defined in `src/soni/core/types.py`
- [ ] Literal types for enums (FlowState, ConversationState)
- [ ] FlowContext TypedDict with all required fields
- [ ] DialogueState TypedDict with all required fields
- [ ] RuntimeContext TypedDict defined
- [ ] Imports working (no circular dependencies)
- [ ] Tests passing in `tests/unit/test_types.py`
- [ ] Mypy passes without errors

### Implementación Detallada

#### Paso 1: Create types.py File

**Archivo(s) a crear/modificar:** `src/soni/core/types.py`

**Código específico:**

```python
from typing import TypedDict, Literal, Any

# Flow states
FlowState = Literal["active", "paused", "completed", "cancelled", "abandoned", "error"]

class FlowContext(TypedDict):
    """Context for a specific instance of a flow."""
    flow_id: str
    flow_name: str
    flow_state: FlowState
    current_step: str | None
    outputs: dict[str, Any]
    started_at: float
    paused_at: float | None
    completed_at: float | None
    context: str | None

class DialogueState(TypedDict):
    """Complete dialogue state for LangGraph."""
    # User communication
    user_message: str
    last_response: str
    messages: list[dict[str, Any]]  # Will use Annotated with add_messages in Phase 4

    # Flow management
    flow_stack: list[FlowContext]
    flow_slots: dict[str, dict[str, Any]]

    # State tracking
    conversation_state: str
    current_step: str | None
    waiting_for_slot: str | None

    # NLU results
    nlu_result: dict[str, Any] | None
    last_nlu_call: float | None

    # Digression tracking
    digression_depth: int
    last_digression_type: str | None

    # Metadata
    turn_count: int
    trace: list[dict[str, Any]]
    metadata: dict[str, Any]

# Conversation states
ConversationState = Literal[
    "idle",
    "understanding",
    "waiting_for_slot",
    "validating_slot",
    "collecting",
    "executing_action",
    "generating_response",
    "error"
]

class RuntimeContext(TypedDict):
    """Runtime context with injected dependencies (for LangGraph context_schema)."""
    flow_manager: Any  # Will be typed properly with interfaces
    nlu_provider: Any
    action_handler: Any
    scope_manager: Any
    normalizer: Any
```

**Explicación:**
- Create the file with all TypedDict definitions
- Use Literal types for enums (FlowState, ConversationState)
- Define FlowContext with all required fields
- Define DialogueState with all required fields for LangGraph
- Define RuntimeContext for dependency injection
- Use `Any` for RuntimeContext fields (will be properly typed in Task 1.2)

#### Paso 2: Create Unit Tests

**Archivo(s) a crear/modificar:** `tests/unit/test_types.py`

**Código específico:**

```python
import pytest
from soni.core.types import FlowContext, DialogueState, ConversationState

def test_flow_context_structure():
    """Test FlowContext has all required fields."""
    # Arrange & Act
    context: FlowContext = {
        "flow_id": "test_123",
        "flow_name": "test_flow",
        "flow_state": "active",
        "current_step": None,
        "outputs": {},
        "started_at": 1234567890.0,
        "paused_at": None,
        "completed_at": None,
        "context": None
    }

    # Assert
    assert context["flow_id"] == "test_123"
    assert context["flow_state"] == "active"

def test_dialogue_state_initialization():
    """Test DialogueState can be initialized with defaults."""
    # Arrange & Act
    state: DialogueState = {
        "user_message": "",
        "last_response": "",
        "messages": [],
        "flow_stack": [],
        "flow_slots": {},
        "conversation_state": "idle",
        "current_step": None,
        "waiting_for_slot": None,
        "nlu_result": None,
        "last_nlu_call": None,
        "digression_depth": 0,
        "last_digression_type": None,
        "turn_count": 0,
        "trace": [],
        "metadata": {}
    }

    # Assert
    assert state["conversation_state"] == "idle"
    assert state["turn_count"] == 0
    assert len(state["flow_stack"]) == 0
```

**Explicación:**
- Create test file with AAA pattern
- Test FlowContext structure and field access
- Test DialogueState initialization with all required fields
- Verify TypedDict behavior works correctly

### Tests Requeridos

**Archivo de tests:** `tests/unit/test_types.py`

**Tests específicos a implementar:**

```python
import pytest
from soni.core.types import FlowContext, DialogueState, ConversationState, FlowState, RuntimeContext

def test_flow_context_structure():
    """Test FlowContext has all required fields."""
    # Arrange & Act
    context: FlowContext = {
        "flow_id": "test_123",
        "flow_name": "test_flow",
        "flow_state": "active",
        "current_step": None,
        "outputs": {},
        "started_at": 1234567890.0,
        "paused_at": None,
        "completed_at": None,
        "context": None
    }

    # Assert
    assert context["flow_id"] == "test_123"
    assert context["flow_state"] == "active"

def test_dialogue_state_initialization():
    """Test DialogueState can be initialized with defaults."""
    # Arrange & Act
    state: DialogueState = {
        "user_message": "",
        "last_response": "",
        "messages": [],
        "flow_stack": [],
        "flow_slots": {},
        "conversation_state": "idle",
        "current_step": None,
        "waiting_for_slot": None,
        "nlu_result": None,
        "last_nlu_call": None,
        "digression_depth": 0,
        "last_digression_type": None,
        "turn_count": 0,
        "trace": [],
        "metadata": {}
    }

    # Assert
    assert state["conversation_state"] == "idle"
    assert state["turn_count"] == 0
    assert len(state["flow_stack"]) == 0

def test_flow_state_literal():
    """Test FlowState literal values are valid."""
    # Arrange & Act
    valid_states: list[FlowState] = ["active", "paused", "completed", "cancelled", "abandoned", "error"]

    # Assert
    assert len(valid_states) == 6
    assert "active" in valid_states

def test_conversation_state_literal():
    """Test ConversationState literal values are valid."""
    # Arrange & Act
    valid_states: list[ConversationState] = [
        "idle", "understanding", "waiting_for_slot", "validating_slot",
        "collecting", "executing_action", "generating_response", "error"
    ]

    # Assert
    assert len(valid_states) == 8
    assert "idle" in valid_states
```

### Criterios de Éxito

- [ ] All TypedDict classes defined
- [ ] Literal types for enums (FlowState, ConversationState)
- [ ] Imports working (no circular dependencies)
- [ ] Tests passing (`uv run pytest tests/unit/test_types.py -v`)
- [ ] Mypy passes (`uv run mypy src/soni/core/types.py`)
- [ ] Ruff passes (`uv run ruff check src/soni/core/types.py`)

### Validación Manual

**Comandos para validar:**

```bash
# Type checking
uv run mypy src/soni/core/types.py

# Tests
uv run pytest tests/unit/test_types.py -v

# Linting
uv run ruff check src/soni/core/types.py
uv run ruff format src/soni/core/types.py
```

**Resultado esperado:**
- Mypy shows no errors
- All tests pass
- Ruff shows no linting errors
- Types can be imported without circular dependency issues

### Referencias

- [docs/implementation/01-phase-1-foundation.md](../../docs/implementation/01-phase-1-foundation.md) - Task 1.1
- [Python TypedDict documentation](https://docs.python.org/3/library/typing.html#typing.TypedDict)
- [LangGraph StateGraph documentation](https://langchain-ai.github.io/langgraph/concepts/low_level/#stategraph)

### Notas Adicionales

- TypedDict is required by LangGraph for state management
- All fields must be properly typed
- Use `| None` for optional fields (Python 3.10+ syntax)
- RuntimeContext uses `Any` temporarily - will be properly typed in Task 1.2
- Messages field will use Annotated with add_messages in Phase 4, but structure is defined now
