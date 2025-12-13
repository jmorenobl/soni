## Task: 2.4 - State Serialization

**ID de tarea:** 204
**Hito:** Phase 2 - State Management & Validation
**Dependencias:** Task 201 (State Transition Validator)
**Duración estimada:** 2-3 horas

### Objetivo

Implement state serialization/deserialization helpers for testing and debugging.

### Contexto

Testing and debugging require state snapshots. This task implements serialization helpers that validate state consistency during deserialization.

**Reference:** [docs/implementation/02-phase-2-state.md](../../docs/implementation/02-phase-2-state.md) - Task 2.4

### Entregables

- [ ] `state_to_dict()` function added to `src/soni/core/state.py`
- [ ] `state_from_dict()` function added to `src/soni/core/state.py`
- [ ] `state_to_json()` function added to `src/soni/core/state.py`
- [ ] `state_from_json()` function added to `src/soni/core/state.py`
- [ ] Deserialization validates state consistency
- [ ] Tests passing in `tests/unit/test_state.py`
- [ ] Mypy passes without errors

### Implementación Detallada

#### Paso 1: Add Serialization Functions

**Archivo(s) a crear/modificar:** `src/soni/core/state.py`

**Código específico:**

```python
import copy
import json
from typing import Any

from soni.core.errors import ValidationError
from soni.core.types import DialogueState
from soni.core.validators import validate_state_consistency

def state_to_dict(state: DialogueState) -> dict[str, Any]:
    """
    Serialize DialogueState to JSON-compatible dict.

    Args:
        state: Dialogue state

    Returns:
        JSON-serializable dictionary
    """
    # DialogueState is already a dict (TypedDict), but ensure deep copy
    return copy.deepcopy(state)

def state_from_dict(data: dict[str, Any]) -> DialogueState:
    """
    Deserialize DialogueState from dict.

    Args:
        data: Dictionary with state data

    Returns:
        DialogueState

    Raises:
        ValidationError: If data is invalid
    """
    # Validate required fields
    required_fields = [
        "user_message", "last_response", "messages",
        "flow_stack", "flow_slots", "conversation_state",
        "turn_count", "trace", "metadata"
    ]

    for field in required_fields:
        if field not in data:
            raise ValidationError(
                f"Missing required field: {field}",
                field=field
            )

    state: DialogueState = data  # type: ignore

    # Validate consistency
    validate_state_consistency(state)

    return state

def state_to_json(state: DialogueState) -> str:
    """Serialize state to JSON string."""
    return json.dumps(state_to_dict(state), indent=2)

def state_from_json(json_str: str) -> DialogueState:
    """Deserialize state from JSON string."""
    data = json.loads(json_str)
    return state_from_dict(data)
```

**Explicación:**
- Add serialization functions to existing `state.py`
- `state_to_dict()` creates deep copy for serialization
- `state_from_dict()` validates required fields and consistency
- `state_to_json()` and `state_from_json()` provide JSON string interface
- Use `validate_state_consistency()` from validators module

#### Paso 2: Add Unit Tests

**Archivo(s) a crear/modificar:** `tests/unit/test_state.py`

**Código específico:**

```python
def test_state_serialization_roundtrip():
    """Test state can be serialized and deserialized."""
    # Arrange
    original = create_initial_state("Hello")

    # Act
    json_str = state_to_json(original)
    restored = state_from_json(json_str)

    # Assert
    assert restored["user_message"] == original["user_message"]
    assert restored["turn_count"] == original["turn_count"]

def test_state_from_dict_validates():
    """Test state_from_dict validates consistency."""
    # Arrange
    invalid_data = {
        "user_message": "test",
        # Missing required fields
    }

    # Act & Assert
    with pytest.raises(ValidationError):
        state_from_dict(invalid_data)
```

**Explicación:**
- Add tests to existing `test_state.py`
- Test roundtrip serialization (dict and JSON)
- Test validation on deserialization
- Follow AAA pattern with clear comments

### Tests Requeridos

**Archivo de tests:** `tests/unit/test_state.py` (add to existing)

**Tests específicos a implementar:**

```python
import pytest
from soni.core.errors import ValidationError
from soni.core.state import (
    create_initial_state,
    state_from_dict,
    state_from_json,
    state_to_dict,
    state_to_json,
)

def test_state_serialization_roundtrip():
    """Test state can be serialized and deserialized."""
    # Arrange
    original = create_initial_state("Hello")

    # Act
    json_str = state_to_json(original)
    restored = state_from_json(json_str)

    # Assert
    assert restored["user_message"] == original["user_message"]
    assert restored["turn_count"] == original["turn_count"]
    assert restored["conversation_state"] == original["conversation_state"]

def test_state_to_dict_creates_copy():
    """Test state_to_dict creates deep copy."""
    # Arrange
    original = create_initial_state("Hello")
    original["turn_count"] = 5

    # Act
    copied = state_to_dict(original)
    copied["turn_count"] = 10

    # Assert
    assert original["turn_count"] == 5
    assert copied["turn_count"] == 10

def test_state_from_dict_validates_missing_fields():
    """Test state_from_dict validates required fields."""
    # Arrange
    invalid_data = {
        "user_message": "test",
        # Missing required fields
    }

    # Act & Assert
    with pytest.raises(ValidationError) as exc_info:
        state_from_dict(invalid_data)

    assert "Missing required field" in str(exc_info.value)

def test_state_from_dict_validates_consistency():
    """Test state_from_dict validates state consistency."""
    # Arrange
    invalid_data = {
        "user_message": "",
        "last_response": "",
        "messages": [],
        "flow_stack": [{
            "flow_id": "test_123",
            "flow_name": "test",
            "flow_state": "active",
            "current_step": None,
            "outputs": {},
            "started_at": 1234567890.0,
            "paused_at": None,
            "completed_at": None,
            "context": None
        }],
        "flow_slots": {},  # Missing slot for flow_stack entry
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

    # Act & Assert
    with pytest.raises(ValidationError) as exc_info:
        state_from_dict(invalid_data)

    assert "missing slot storage" in str(exc_info.value)
```

### Criterios de Éxito

- [ ] Serialization implemented
- [ ] Deserialization implemented
- [ ] Validation integrated
- [ ] Roundtrip tests passing
- [ ] Tests passing (`uv run pytest tests/unit/test_state.py -v`)
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
- Serialization/deserialization working correctly

### Referencias

- [docs/implementation/02-phase-2-state.md](../../docs/implementation/02-phase-2-state.md) - Task 2.4

### Notas Adicionales

- Serialization creates deep copies to prevent mutation
- Deserialization validates both structure and consistency
- JSON functions use standard library json module
- Required fields list matches DialogueState TypedDict structure
