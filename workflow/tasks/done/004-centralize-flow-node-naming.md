## Task: 004 - Centralize Flow Node Naming Convention

**ID de tarea:** 004
**Hito:** DRY / Maintainability
**Dependencias:** Ninguna
**Duración estimada:** 1 hora

### Objetivo

Centralizar el patrón `flow_{flow_name}` en una función helper única para evitar strings mágicos duplicados.

### Contexto

El patrón está repetido manualmente:

```python
# dm/builder.py:40
node_name = f"flow_{flow_name}"

# dm/nodes/execute.py:74
target = f"flow_{active_ctx['flow_name']}"
```

Si el patrón cambia, hay que actualizar múltiples lugares.

### Entregables

- [ ] Crear función `get_flow_node_name(flow_name: str) -> str` en `core/constants.py`
- [ ] Actualizar `dm/builder.py` para usar la función
- [ ] Actualizar `dm/nodes/execute.py` para usar la función
- [ ] Tests verificando consistencia

### Implementación Detallada

#### Paso 1: Añadir helper a constants

**Archivo(s) a modificar:** `src/soni/core/constants.py`

```python
def get_flow_node_name(flow_name: str) -> str:
    """Generate LangGraph node name for a flow.

    Centralizes the naming convention to avoid magic strings.

    Args:
        flow_name: Name of the flow (e.g., "book_flight")

    Returns:
        Node name for LangGraph (e.g., "flow_book_flight")
    """
    return f"flow_{flow_name}"
```

#### Paso 2: Actualizar dm/builder.py

```python
from soni.core.constants import get_flow_node_name

# Line ~40
node_name = get_flow_node_name(flow_name)
```

#### Paso 3: Actualizar dm/nodes/execute.py

```python
from soni.core.constants import get_flow_node_name

# Line ~74
target = get_flow_node_name(active_ctx['flow_name'])
```

### TDD Cycle (MANDATORY)

#### Red Phase: Write Failing Tests

**Test file:** `tests/unit/core/test_constants_helpers.py`

```python
import pytest
from soni.core.constants import get_flow_node_name


class TestGetFlowNodeName:
    """Tests for flow node naming helper."""

    def test_generates_correct_prefix(self):
        """Test that node name has flow_ prefix."""
        # Arrange
        flow_name = "book_flight"

        # Act
        result = get_flow_node_name(flow_name)

        # Assert
        assert result == "flow_book_flight"

    def test_handles_underscore_in_name(self):
        """Test names with underscores work correctly."""
        # Arrange
        flow_name = "transfer_funds"

        # Act
        result = get_flow_node_name(flow_name)

        # Assert
        assert result == "flow_transfer_funds"

    def test_consistent_with_builder(self):
        """Test that result matches pattern used in builder."""
        # Arrange
        flow_name = "test_flow"

        # Act
        helper_result = get_flow_node_name(flow_name)
        manual_result = f"flow_{flow_name}"

        # Assert
        assert helper_result == manual_result
```

**Verify tests fail:**
```bash
uv run pytest tests/unit/core/test_constants_helpers.py -v
# Expected: FAILED (function doesn't exist)
```

#### Green Phase: Make Tests Pass

Implementar la función y actualizar los usos.

```bash
uv run pytest tests/unit/core/test_constants_helpers.py -v
# Expected: PASSED ✅
```

### Criterios de Éxito

- [ ] Función `get_flow_node_name()` existe en `core/constants.py`
- [ ] `dm/builder.py` usa la función
- [ ] `dm/nodes/execute.py` usa la función
- [ ] No hay `f"flow_{` hardcodeados
- [ ] `uv run pytest` pasa
- [ ] `uv run ruff check .` sin errores
- [ ] `uv run mypy src/soni` sin errores

### Validación Manual

```bash
# Verificar no hay duplicados
grep -r 'f"flow_' src/soni/ --include="*.py"
# Debería mostrar solo el helper en constants.py

uv run pytest tests/ -v
```

### Referencias

- `src/soni/dm/builder.py:40` - Uso en builder
- `src/soni/dm/nodes/execute.py:74` - Uso en execute
