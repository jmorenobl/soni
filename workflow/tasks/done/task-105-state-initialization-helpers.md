## Task: 1.5 - State Initialization Helpers

**ID de tarea:** 105
**Hito:** Phase 1 - Core Foundation
**Dependencias:** Task 101 (Core Type Definitions)
**Duración estimada:** 1-2 horas

### Objetivo

Create helper functions for DialogueState initialization to reduce boilerplate and ensure consistent state initialization throughout the framework.

### Contexto

These helper functions provide a clean way to create DialogueState instances with proper defaults, reducing the chance of errors from manual state creation and ensuring consistency across the codebase.

**Reference:** [docs/implementation/01-phase-1-foundation.md](../../docs/implementation/01-phase-1-foundation.md) - Task 1.5

### Entregables

- [ ] create_empty_state() function implemented
- [ ] create_initial_state() function implemented
- [ ] Helper functions in `src/soni/core/state.py`
- [ ] Tests passing in `tests/unit/test_state.py`
- [ ] Docstrings present for all functions

### Implementación Detallada

#### Paso 1: Create state.py File with Helper Functions

**Archivo(s) a crear/modificar:** `src/soni/core/state.py`

**Código específico:**

```python
from soni.core.types import DialogueState
import time

def create_empty_state() -> DialogueState:
    """Create an empty DialogueState with defaults."""
    return {
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

def create_initial_state(user_message: str) -> DialogueState:
    """Create initial state for new conversation."""
    state = create_empty_state()
    state["user_message"] = user_message
    state["conversation_state"] = "understanding"
    state["turn_count"] = 1
    state["trace"] = [{
        "turn": 1,
        "user_message": user_message,
        "timestamp": time.time()
    }]
    return state
```

**Explicación:**
- Create helper functions for state initialization
- create_empty_state() returns a DialogueState with all defaults
- create_initial_state() creates state for a new conversation with user message
- Use time.time() for timestamps
- Ensure all required fields are present with correct types

#### Paso 2: Create Unit Tests

**Archivo(s) a crear/modificar:** `tests/unit/test_state.py`

**Código específico:**

```python
import pytest
from soni.core.state import create_empty_state, create_initial_state

def test_create_empty_state():
    """Test create_empty_state returns valid state."""
    # Arrange & Act
    state = create_empty_state()

    # Assert
    assert state["conversation_state"] == "idle"
    assert state["turn_count"] == 0
    assert len(state["flow_stack"]) == 0
    assert state["user_message"] == ""
    assert state["last_response"] == ""
    assert len(state["messages"]) == 0
    assert len(state["flow_slots"]) == 0

def test_create_initial_state():
    """Test create_initial_state with message."""
    # Arrange & Act
    state = create_initial_state("Hello")

    # Assert
    assert state["user_message"] == "Hello"
    assert state["conversation_state"] == "understanding"
    assert state["turn_count"] == 1
    assert len(state["trace"]) == 1
    assert state["trace"][0]["user_message"] == "Hello"
    assert state["trace"][0]["turn"] == 1
```

**Explicación:**
- Test create_empty_state returns valid state with all defaults
- Test create_initial_state initializes state correctly with user message
- Verify all required fields are present
- Verify trace is initialized correctly

### Tests Requeridos

**Archivo de tests:** `tests/unit/test_state.py`

**Tests específicos a implementar:**

```python
import pytest
from soni.core.state import create_empty_state, create_initial_state
from soni.core.types import DialogueState

def test_create_empty_state():
    """Test create_empty_state returns valid state."""
    # Arrange & Act
    state = create_empty_state()

    # Assert
    assert state["conversation_state"] == "idle"
    assert state["turn_count"] == 0
    assert len(state["flow_stack"]) == 0
    assert state["user_message"] == ""
    assert state["last_response"] == ""
    assert len(state["messages"]) == 0
    assert len(state["flow_slots"]) == 0
    assert state["nlu_result"] is None
    assert state["last_nlu_call"] is None
    assert state["digression_depth"] == 0
    assert state["last_digression_type"] is None
    assert len(state["trace"]) == 0
    assert isinstance(state["metadata"], dict)

def test_create_initial_state():
    """Test create_initial_state with message."""
    # Arrange & Act
    state = create_initial_state("Hello")

    # Assert
    assert state["user_message"] == "Hello"
    assert state["conversation_state"] == "understanding"
    assert state["turn_count"] == 1
    assert len(state["trace"]) == 1
    assert state["trace"][0]["user_message"] == "Hello"
    assert state["trace"][0]["turn"] == 1
    assert "timestamp" in state["trace"][0]

def test_create_initial_state_uses_empty_state():
    """Test create_initial_state builds on create_empty_state."""
    # Arrange & Act
    state = create_initial_state("Test message")

    # Assert - verify it has all fields from empty_state
    assert "flow_stack" in state
    assert "flow_slots" in state
    assert "messages" in state
    # And has overridden values
    assert state["user_message"] == "Test message"
    assert state["conversation_state"] == "understanding"
```

### Criterios de Éxito

- [ ] Helper functions implemented
- [ ] Tests passing (`uv run pytest tests/unit/test_state.py -v`)
- [ ] Docstrings present for all functions
- [ ] Mypy passes (`uv run mypy src/soni/core/state.py`)
- [ ] Ruff passes (`uv run ruff check src/soni/core/state.py`)

### Validación Manual

**Comandos para validar:**

```bash
# Type checking
uv run mypy src/soni/core/state.py

# Tests
uv run pytest tests/unit/test_state.py -v

# Linting
uv run ruff check src/soni/core/state.py
uv run ruff format src/soni/core/state.py
```

**Resultado esperado:**
- Mypy shows no errors
- All tests pass
- Ruff shows no linting errors
- Helper functions return valid DialogueState instances
- create_initial_state properly initializes trace

### Referencias

- [docs/implementation/01-phase-1-foundation.md](../../docs/implementation/01-phase-1-foundation.md) - Task 1.5

### Notas Adicionales

- Helper functions reduce boilerplate and ensure consistency
- create_empty_state() is used as base for create_initial_state()
- Trace is initialized with first turn information
- All fields must match DialogueState TypedDict exactly
- Use time.time() for Unix timestamps
