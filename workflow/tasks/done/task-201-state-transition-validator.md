## Task: 2.1 - State Transition Validator

**ID de tarea:** 201
**Hito:** Phase 2 - State Management & Validation
**Dependencias:** Ninguna
**Duración estimada:** 2-3 horas

### Objetivo

Implement state transition validation based on state machine to ensure state transitions follow the designed state machine.

### Contexto

This is the foundational task for Phase 2. State transition validation ensures that conversation state changes follow the designed state machine (see `docs/design/04-state-machine.md`). This validation is required before implementing state update wrappers and serialization.

**Reference:** [docs/implementation/02-phase-2-state.md](../../docs/implementation/02-phase-2-state.md) - Task 2.1

### Entregables

- [ ] `src/soni/core/validators.py` created with transition validation
- [ ] `validate_transition()` function implemented
- [ ] `validate_state_consistency()` function implemented
- [ ] `VALID_TRANSITIONS` dictionary defined
- [ ] Tests passing in `tests/unit/test_validators.py`
- [ ] Mypy passes without errors

### Implementación Detallada

#### Paso 1: Create validators.py File

**Archivo(s) a crear/modificar:** `src/soni/core/validators.py`

**Código específico:**

```python
"""State validation for Soni Framework."""

from soni.core.errors import ValidationError
from soni.core.types import DialogueState

# Valid state transitions (see state machine diagram)
VALID_TRANSITIONS: dict[str, list[str]] = {
    "idle": ["understanding"],
    "understanding": ["waiting_for_slot", "validating_slot", "executing_action", "error", "idle"],
    "waiting_for_slot": ["understanding"],
    "validating_slot": ["collecting", "waiting_for_slot", "error"],
    "collecting": ["understanding", "validating_slot", "executing_action"],
    "executing_action": ["generating_response", "error"],
    "generating_response": ["idle", "understanding"],
    "error": ["idle", "understanding"]
}

def validate_transition(
    current_state: str,
    next_state: str
) -> None:
    """
    Validate state transition is allowed.

    Args:
        current_state: Current conversation state
        next_state: Target conversation state

    Raises:
        ValidationError: If transition is not valid
    """
    valid_next_states = VALID_TRANSITIONS.get(current_state, [])

    if next_state not in valid_next_states:
        raise ValidationError(
            f"Invalid state transition: {current_state} → {next_state}",
            current=current_state,
            next=next_state,
            valid_transitions=valid_next_states
        )

def validate_state_consistency(state: DialogueState) -> None:
    """
    Validate state internal consistency.

    Args:
        state: Dialogue state to validate

    Raises:
        ValidationError: If state is inconsistent
    """
    # Check flow_stack consistency
    active_flow_ids = {ctx["flow_id"] for ctx in state["flow_stack"]}
    slot_flow_ids = set(state["flow_slots"].keys())

    # All active flows must have slots
    missing_slots = active_flow_ids - slot_flow_ids
    if missing_slots:
        raise ValidationError(
            "Active flows missing slot storage",
            missing=list(missing_slots)
        )

    # Check waiting_for_slot requires active flow
    if state["waiting_for_slot"] and not state["flow_stack"]:
        raise ValidationError(
            "Cannot wait for slot without active flow",
            slot=state["waiting_for_slot"]
        )

    # Check conversation_state consistency
    if state["conversation_state"] == "waiting_for_slot":
        if not state["waiting_for_slot"]:
            raise ValidationError(
                "State is waiting_for_slot but waiting_for_slot is None"
            )
```

**Explicación:**
- Create new file `src/soni/core/validators.py`
- Define `VALID_TRANSITIONS` dictionary with all valid state transitions
- Implement `validate_transition()` to check if transition is allowed
- Implement `validate_state_consistency()` to check internal state consistency
- Use `ValidationError` from `soni.core.errors` for error reporting

#### Paso 2: Create Unit Tests

**Archivo(s) a crear/modificar:** `tests/unit/test_validators.py`

**Código específico:**

```python
"""Unit tests for state validators."""

import pytest

from soni.core.errors import ValidationError
from soni.core.state import create_empty_state
from soni.core.validators import validate_state_consistency, validate_transition


def test_valid_transition_allowed():
    """Test valid transition doesn't raise error."""
    # Arrange & Act & Assert
    validate_transition("idle", "understanding")  # Should not raise


def test_invalid_transition_raises():
    """Test invalid transition raises ValidationError."""
    # Arrange & Act & Assert
    with pytest.raises(ValidationError) as exc_info:
        validate_transition("idle", "executing_action")

    assert "Invalid state transition" in str(exc_info.value)


def test_state_consistency_valid():
    """Test consistent state passes validation."""
    # Arrange
    state = create_empty_state()

    # Act & Assert
    validate_state_consistency(state)  # Should not raise


def test_state_consistency_missing_slots():
    """Test validation fails when flow has no slots."""
    # Arrange
    state = create_empty_state()
    state["flow_stack"].append({
        "flow_id": "test_123",
        "flow_name": "test",
        "flow_state": "active",
        "current_step": None,
        "outputs": {},
        "started_at": 1234567890.0,
        "paused_at": None,
        "completed_at": None,
        "context": None
    })
    # Note: flow_slots is empty

    # Act & Assert
    with pytest.raises(ValidationError) as exc_info:
        validate_state_consistency(state)

    assert "missing slot storage" in str(exc_info.value)
```

**Explicación:**
- Create test file with AAA pattern
- Test valid transitions don't raise errors
- Test invalid transitions raise ValidationError
- Test state consistency validation for valid states
- Test state consistency validation for invalid states (missing slots)

### Tests Requeridos

**Archivo de tests:** `tests/unit/test_validators.py`

**Tests específicos a implementar:**

```python
"""Unit tests for state validators."""

import pytest

from soni.core.errors import ValidationError
from soni.core.state import create_empty_state
from soni.core.validators import validate_state_consistency, validate_transition


def test_valid_transition_allowed():
    """Test valid transition doesn't raise error."""
    # Arrange & Act & Assert
    validate_transition("idle", "understanding")  # Should not raise


def test_invalid_transition_raises():
    """Test invalid transition raises ValidationError."""
    # Arrange & Act & Assert
    with pytest.raises(ValidationError) as exc_info:
        validate_transition("idle", "executing_action")

    assert "Invalid state transition" in str(exc_info.value)


def test_state_consistency_valid():
    """Test consistent state passes validation."""
    # Arrange
    state = create_empty_state()

    # Act & Assert
    validate_state_consistency(state)  # Should not raise


def test_state_consistency_missing_slots():
    """Test validation fails when flow has no slots."""
    # Arrange
    state = create_empty_state()
    state["flow_stack"].append({
        "flow_id": "test_123",
        "flow_name": "test",
        "flow_state": "active",
        "current_step": None,
        "outputs": {},
        "started_at": 1234567890.0,
        "paused_at": None,
        "completed_at": None,
        "context": None
    })
    # Note: flow_slots is empty

    # Act & Assert
    with pytest.raises(ValidationError) as exc_info:
        validate_state_consistency(state)

    assert "missing slot storage" in str(exc_info.value)
```

### Criterios de Éxito

- [ ] Transition validation implemented
- [ ] State consistency validation implemented
- [ ] Tests passing (`uv run pytest tests/unit/test_validators.py -v`)
- [ ] Mypy passes (`uv run mypy src/soni/core/validators.py`)
- [ ] Ruff passes (`uv run ruff check src/soni/core/validators.py`)

### Validación Manual

**Comandos para validar:**

```bash
# Type checking
uv run mypy src/soni/core/validators.py

# Tests
uv run pytest tests/unit/test_validators.py -v

# Linting
uv run ruff check src/soni/core/validators.py
uv run ruff format src/soni/core/validators.py
```

**Resultado esperado:**
- Mypy shows no errors
- All tests pass
- Ruff shows no linting errors
- Validators can be imported without errors

### Referencias

- [docs/implementation/02-phase-2-state.md](../../docs/implementation/02-phase-2-state.md) - Task 2.1
- [docs/design/04-state-machine.md](../../docs/design/04-state-machine.md) - State machine design

### Notas Adicionales

- Valid transitions are based on the state machine diagram in design docs
- State consistency checks ensure flow_stack and flow_slots are synchronized
- Validation errors include context for debugging
