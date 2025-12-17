## Task: 001 - Consolidate FlowState and FlowContextState Types

**ID de tarea:** 001
**Hito:** Architectural Cleanup
**Dependencias:** Ninguna
**Duración estimada:** 2 horas

### Objetivo

Eliminar la duplicación de tipos `FlowState` y `FlowContextState` que están definidos tanto como `Literal` en `core/types.py` como `StrEnum` en `core/constants.py`. Usar únicamente las versiones `StrEnum`.

### Contexto

Actualmente existen definiciones duplicadas:
- `core/types.py:20`: `FlowState = Literal["idle", "active", "waiting_input", "done", "error"]`
- `core/constants.py:9-16`: `class FlowState(StrEnum)`

Esto causa:
1. Shadowing cuando se importan ambos
2. Confusión sobre cuál usar
3. Incompatibilidad de tipos en mypy

### Entregables

- [ ] Eliminar `FlowState` Literal de `core/types.py`
- [ ] Eliminar `FlowContextState` Literal de `core/types.py`
- [ ] Actualizar todas las importaciones para usar `core/constants`
- [ ] Actualizar type hints en `FlowContext` y `DialogueState`
- [ ] Tests pasan, ruff y mypy sin errores

### Implementación Detallada

#### Paso 1: Actualizar `core/types.py`

**Archivo(s) a modificar:** `src/soni/core/types.py`

```python
# ELIMINAR líneas 20-21:
# FlowState = Literal["idle", "active", "waiting_input", "done", "error"]
# FlowContextState = Literal["active", "completed", "cancelled"]

# AÑADIR import:
from soni.core.constants import FlowState, FlowContextState
```

#### Paso 2: Actualizar TypedDicts

**Archivo(s) a modificar:** `src/soni/core/types.py`

```python
class FlowContext(TypedDict):
    flow_state: FlowContextState  # Ahora usa StrEnum
    # ... resto igual

class DialogueState(TypedDict):
    flow_state: FlowState  # Ahora usa StrEnum
    # ... resto igual
```

#### Paso 3: Actualizar imports en módulos que usan estos tipos

**Archivos a revisar:**
- `src/soni/dm/nodes/*.py`
- `src/soni/compiler/nodes/*.py`
- `src/soni/flow/manager.py`

### TDD Cycle (MANDATORY)

#### Red Phase: Write Failing Tests

**Test file:** `tests/unit/core/test_type_consistency.py`

```python
import pytest
from soni.core.constants import FlowState, FlowContextState
from soni.core.types import DialogueState, FlowContext


def test_flow_state_is_strenum():
    """Test that FlowState is a StrEnum, not Literal."""
    # Arrange
    from enum import StrEnum

    # Act & Assert
    assert issubclass(FlowState, StrEnum)
    assert FlowState.IDLE == "idle"
    assert FlowState.ACTIVE == "active"


def test_flow_context_state_is_strenum():
    """Test that FlowContextState is a StrEnum."""
    # Arrange
    from enum import StrEnum

    # Act & Assert
    assert issubclass(FlowContextState, StrEnum)


def test_no_duplicate_flow_state_in_types():
    """Test that types.py doesn't define its own FlowState Literal."""
    # Arrange
    import soni.core.types as types_module

    # Act
    module_dict = vars(types_module)

    # Assert - should import from constants, not define new
    # FlowState in types should BE the same as constants
    from soni.core.constants import FlowState as ConstFlowState
    assert types_module.FlowState is ConstFlowState
```

**Verify tests fail:**
```bash
uv run pytest tests/unit/core/test_type_consistency.py -v
# Expected: FAILED (duplicates still exist)
```

#### Green Phase: Make Tests Pass

Implementar cambios descritos en "Implementación Detallada".

```bash
uv run pytest tests/unit/core/test_type_consistency.py -v
# Expected: PASSED ✅
```

### Criterios de Éxito

- [ ] No existe `FlowState = Literal[...]` en `core/types.py`
- [ ] No existe `FlowContextState = Literal[...]` en `core/types.py`
- [ ] Imports correctos desde `core/constants`
- [ ] `uv run pytest` pasa
- [ ] `uv run ruff check .` sin errores
- [ ] `uv run mypy src/soni` sin errores

### Validación Manual

```bash
uv run pytest tests/ -v
uv run ruff check . && ruff format .
uv run mypy src/soni
```

### Referencias

- `src/soni/core/types.py:20-21` - Definiciones Literal a eliminar
- `src/soni/core/constants.py:9-25` - StrEnums canónicas
