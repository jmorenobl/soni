## Task: 2.2 - State Update Wrapper

**ID de tarea:** 202
**Hito:** Phase 2 - State Management & Validation
**Dependencias:** Task 201 (State Transition Validator)
**Duración estimada:** 1-2 horas

### Objetivo

Create safe state update function with validation to ensure all state updates are validated before applying.

### Contexto

This task builds on Task 201 to provide a safe wrapper for state updates. All state modifications should go through this function to ensure transitions are valid and state remains consistent.

**Reference:** [docs/implementation/02-phase-2-state.md](../../docs/implementation/02-phase-2-state.md) - Task 2.2

### Entregables

- [ ] `update_state()` function added to `src/soni/core/state.py`
- [ ] Function validates transitions before applying updates
- [ ] Function validates state consistency after updates
- [ ] Tests passing in `tests/unit/test_state.py`
- [ ] Mypy passes without errors

### Implementación Detallada

#### Paso 1: Add update_state Function

**Archivo(s) a crear/modificar:** `src/soni/core/state.py`

**Código específico:**

```python
from typing import Any
from soni.core.validators import validate_transition, validate_state_consistency
from soni.core.types import DialogueState

def update_state(
    state: DialogueState,
    updates: dict[str, Any],
    validate: bool = True
) -> None:
    """
    Update dialogue state with validation.

    Args:
        state: Current dialogue state (modified in place)
        updates: Partial updates to apply
        validate: Whether to validate transition (default True)

    Raises:
        ValidationError: If update would create invalid state
    """
    # Validate conversation_state transition if changing
    if validate and "conversation_state" in updates:
        validate_transition(
            state["conversation_state"],
            updates["conversation_state"]
        )

    # Apply updates
    for key, value in updates.items():
        if key in state:
            state[key] = value  # type: ignore

    # Validate final state consistency
    if validate:
        validate_state_consistency(state)
```

**Explicación:**
- Add `update_state()` function to existing `state.py`
- Import validators from `soni.core.validators`
- Validate transition if `conversation_state` is being updated
- Apply all updates to state
- Validate final state consistency
- Use `validate` parameter to allow skipping validation when needed

#### Paso 2: Add Unit Tests

**Archivo(s) a crear/modificar:** `tests/unit/test_state.py`

**Código específico:**

```python
def test_update_state_valid_transition():
    """Test update_state with valid transition."""
    # Arrange
    state = create_empty_state()
    state["conversation_state"] = "idle"

    # Act
    update_state(state, {"conversation_state": "understanding"})

    # Assert
    assert state["conversation_state"] == "understanding"

def test_update_state_invalid_transition_raises():
    """Test update_state with invalid transition raises."""
    # Arrange
    state = create_empty_state()
    state["conversation_state"] = "idle"

    # Act & Assert
    with pytest.raises(ValidationError):
        update_state(state, {"conversation_state": "executing_action"})
```

**Explicación:**
- Add tests to existing `test_state.py`
- Test valid transitions work correctly
- Test invalid transitions raise ValidationError
- Follow AAA pattern with clear comments

### Tests Requeridos

**Archivo de tests:** `tests/unit/test_state.py` (add to existing)

**Tests específicos a implementar:**

```python
import pytest
from soni.core.errors import ValidationError
from soni.core.state import create_empty_state, update_state

def test_update_state_valid_transition():
    """Test update_state with valid transition."""
    # Arrange
    state = create_empty_state()
    state["conversation_state"] = "idle"

    # Act
    update_state(state, {"conversation_state": "understanding"})

    # Assert
    assert state["conversation_state"] == "understanding"

def test_update_state_invalid_transition_raises():
    """Test update_state with invalid transition raises."""
    # Arrange
    state = create_empty_state()
    state["conversation_state"] = "idle"

    # Act & Assert
    with pytest.raises(ValidationError):
        update_state(state, {"conversation_state": "executing_action")

def test_update_state_multiple_fields():
    """Test update_state can update multiple fields."""
    # Arrange
    state = create_empty_state()

    # Act
    update_state(state, {"turn_count": 5, "user_message": "Hello"})

    # Assert
    assert state["turn_count"] == 5
    assert state["user_message"] == "Hello"

def test_update_state_skip_validation():
    """Test update_state can skip validation."""
    # Arrange
    state = create_empty_state()
    state["conversation_state"] = "idle"

    # Act & Assert - Should not raise even with invalid transition
    update_state(state, {"conversation_state": "executing_action"}, validate=False)
    assert state["conversation_state"] == "executing_action"
```

### Criterios de Éxito

- [ ] Update wrapper implemented
- [ ] Validation integration working
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
- State updates work correctly with validation

### Referencias

- [docs/implementation/02-phase-2-state.md](../../docs/implementation/02-phase-2-state.md) - Task 2.2

### Notas Adicionales

- Function modifies state in place (mutable TypedDict)
- Validation can be skipped for special cases (e.g., initialization)
- All state updates should use this function for consistency
