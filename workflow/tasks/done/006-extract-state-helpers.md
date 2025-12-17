## Task: 006 - Extract Common State Helper Functions

**ID de tarea:** 006
**Hito:** DRY / Maintainability
**Dependencias:** 001 (usar StrEnums)
**Duración estimada:** 1.5 horas

### Objetivo

Extraer patrones de acceso a estado repetidos en helpers centralizados para mejorar DRY.

### Contexto

El patrón `state.get("flow_state") == "waiting_input"` está repetido en:
- `compiler/subgraph.py:217`
- `dm/nodes/resume.py:110`
- `dm/builder.py:57`

Similar para otras comprobaciones de estado.

### Entregables

- [ ] Crear `src/soni/core/state_helpers.py`
- [ ] Implementar `is_waiting_for_input(state)`, `is_flow_active(state)`, etc.
- [ ] Actualizar módulos para usar helpers
- [ ] Tests unitarios

### Implementación Detallada

#### Paso 1: Crear módulo de helpers

**Archivo(s) a crear:** `src/soni/core/state_helpers.py`

```python
"""State access helpers to reduce duplication.

Centralizes common state checks used across nodes.
"""

from soni.core.constants import FlowState
from soni.core.types import DialogueState


def is_waiting_for_input(state: DialogueState) -> bool:
    """Check if dialogue is paused waiting for user input."""
    return state.get("flow_state") == FlowState.WAITING_INPUT


def is_flow_active(state: DialogueState) -> bool:
    """Check if there's an active flow executing."""
    return bool(state.get("flow_stack"))


def has_active_flow(state: DialogueState) -> bool:
    """Alias for is_flow_active for readability."""
    return is_flow_active(state)


def get_current_flow_name(state: DialogueState) -> str | None:
    """Get the name of the currently active flow, or None."""
    stack = state.get("flow_stack", [])
    if stack:
        return stack[-1].get("flow_name")
    return None
```

#### Paso 2: Actualizar usos

**Archivos a modificar:**
- `src/soni/compiler/subgraph.py`
- `src/soni/dm/nodes/resume.py`
- `src/soni/dm/builder.py`

```python
# Antes:
if state.get("flow_state") == "waiting_input":

# Después:
from soni.core.state_helpers import is_waiting_for_input

if is_waiting_for_input(state):
```

### TDD Cycle (MANDATORY)

#### Red Phase: Write Failing Tests

**Test file:** `tests/unit/core/test_state_helpers.py`

```python
import pytest
from soni.core.state_helpers import (
    is_waiting_for_input,
    is_flow_active,
    get_current_flow_name,
)
from soni.core.state import create_empty_dialogue_state


class TestIsWaitingForInput:
    """Tests for is_waiting_for_input helper."""

    def test_returns_true_when_waiting(self):
        """Test detection of waiting_input state."""
        # Arrange
        state = create_empty_dialogue_state()
        state["flow_state"] = "waiting_input"

        # Act
        result = is_waiting_for_input(state)

        # Assert
        assert result is True

    def test_returns_false_when_active(self):
        """Test returns False for active state."""
        # Arrange
        state = create_empty_dialogue_state()
        state["flow_state"] = "active"

        # Act
        result = is_waiting_for_input(state)

        # Assert
        assert result is False


class TestIsFlowActive:
    """Tests for is_flow_active helper."""

    def test_returns_true_with_stack(self):
        """Test returns True when flow_stack has items."""
        # Arrange
        state = create_empty_dialogue_state()
        state["flow_stack"] = [{"flow_id": "test", "flow_name": "test_flow"}]

        # Act
        result = is_flow_active(state)

        # Assert
        assert result is True

    def test_returns_false_empty_stack(self):
        """Test returns False when flow_stack is empty."""
        # Arrange
        state = create_empty_dialogue_state()
        state["flow_stack"] = []

        # Act
        result = is_flow_active(state)

        # Assert
        assert result is False


class TestGetCurrentFlowName:
    """Tests for get_current_flow_name helper."""

    def test_returns_flow_name_from_stack(self):
        """Test returns the flow_name of top stack item."""
        # Arrange
        state = create_empty_dialogue_state()
        state["flow_stack"] = [
            {"flow_id": "1", "flow_name": "first"},
            {"flow_id": "2", "flow_name": "second"},
        ]

        # Act
        result = get_current_flow_name(state)

        # Assert
        assert result == "second"

    def test_returns_none_empty_stack(self):
        """Test returns None when stack is empty."""
        # Arrange
        state = create_empty_dialogue_state()

        # Act
        result = get_current_flow_name(state)

        # Assert
        assert result is None
```

**Verify tests fail:**
```bash
uv run pytest tests/unit/core/test_state_helpers.py -v
# Expected: FAILED (module doesn't exist)
```

#### Green Phase: Make Tests Pass

Crear el módulo y actualizar usos.

```bash
uv run pytest tests/unit/core/test_state_helpers.py -v
# Expected: PASSED ✅
```

### Criterios de Éxito

- [ ] `state_helpers.py` existe con funciones helper
- [ ] No hay `state.get("flow_state") == "waiting_input"` directo
- [ ] Todos los módulos usan helpers
- [ ] `uv run pytest` pasa
- [ ] `uv run ruff check .` sin errores
- [ ] `uv run mypy src/soni` sin errores

### Validación Manual

```bash
# Verificar no hay accesos directos
grep -r '"waiting_input"' src/soni/ --include="*.py" | grep -v state_helpers
# Debería estar vacío o solo en constants

uv run pytest tests/ -v
```

### Referencias

- `src/soni/compiler/subgraph.py:217`
- `src/soni/dm/nodes/resume.py:110`
- `src/soni/dm/builder.py:57`
