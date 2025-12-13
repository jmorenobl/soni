## Task: 325 - Tests para Patrón CANCELLATION

**ID de tarea:** 325
**Hito:** Fase 1 - Critical Fixes
**Dependencias:** Ninguna
**Duración estimada:** 4-5 horas
**Prioridad:** 🔴 CRÍTICA

### Objetivo

Crear tests unitarios exhaustivos para el patrón conversacional CANCELLATION, que actualmente tiene solo 30% de cobertura (solo routing básico). Este patrón permite a los usuarios cancelar el flujo actual en cualquier momento.

### Contexto

Según el informe de conformidad (`docs/analysis/INFORME_CONFORMIDAD_DISENO_TESTS.md`), el patrón CANCELLATION es un gap crítico. El diseño especifica (`docs/design/10-dsl-specification/06-patterns.md:20-48`):

```
User: "Forget it, cancel everything"
→ Runtime detects CANCELLATION
→ Current flow is popped from stack
→ Returns to parent flow or idle state
→ Can happen during ANY step (collect, confirm, action)
```

**Impacto**: CRÍTICO - Usuarios deben poder cancelar en cualquier momento, funcionalidad core sin tests.

**Estado actual**:
- Nodo `handle_cancellation_node` existe en `src/soni/dm/nodes/handle_cancellation.py`
- Solo existe test básico de routing en `test_routing.py`
- **NO hay tests del nodo mismo**

### Entregables

- [ ] Archivo `tests/unit/test_dm_nodes_handle_cancellation.py` creado
- [ ] Mínimo 5 tests unitarios implementados cubriendo todos los escenarios
- [ ] Tests verifican pop de flow durante slot collection
- [ ] Tests verifican pop de flow durante confirmation
- [ ] Tests verifican pop a parent flow cuando hay múltiples flows
- [ ] Tests verifican limpieza de metadata
- [ ] Todos los tests pasan con cobertura >90% del nodo
- [ ] Tests siguen patrón AAA y usan fixtures de conftest.py

### Implementación Detallada

#### Paso 1: Crear archivo de tests

**Archivo(s) a crear:** `tests/unit/test_dm_nodes_handle_cancellation.py`

**Estructura base:**

```python
"""Tests for handle_cancellation node."""

import pytest
from unittest.mock import AsyncMock, MagicMock

from soni.core.types import DialogueState, MessageType
from soni.du.types import NLUOutput
from soni.dm.nodes.handle_cancellation import handle_cancellation_node


@pytest.fixture
def mock_runtime():
    """Create mock runtime context."""
    runtime = AsyncMock()
    runtime.context = {
        "flow_manager": MagicMock(),
        "step_manager": AsyncMock(),
    }
    return runtime
```

#### Paso 2: Implementar test de cancellation durante slot collection

**Archivo(s) a modificar:** `tests/unit/test_dm_nodes_handle_cancellation.py`

**Código específico:**

```python
async def test_handle_cancellation_during_slot_collection(
    create_state_with_flow, mock_runtime
):
    """
    User cancels while collecting slots.

    Design Reference: docs/design/10-dsl-specification/06-patterns.md:20-48
    Pattern: "Cancellation can happen during ANY step (collect, confirm, action)"
    """
    # Arrange
    state = create_state_with_flow("book_flight")
    state["flow_stack"] = [{"flow_id": "flow_1", "flow_name": "book_flight"}]
    state["waiting_for_slot"] = "origin"
    state["conversation_state"] = "waiting_for_slot"
    state["nlu_result"] = {
        "message_type": MessageType.CANCELLATION.value,
    }

    # Mock flow_manager.pop_flow
    def mock_pop_flow(state, result):
        state["flow_stack"].pop()
        state["flow_slots"].pop("flow_1", None)

    mock_runtime.context["flow_manager"].pop_flow.side_effect = mock_pop_flow
    mock_runtime.context["flow_manager"].get_active_context.return_value = {
        "flow_id": "flow_1",
        "flow_name": "book_flight",
    }

    # Act
    result = await handle_cancellation_node(state, mock_runtime)

    # Assert
    # ✅ Flow popped from stack
    assert len(result["flow_stack"]) == 0
    # ✅ Returns to idle
    assert result["conversation_state"] == "idle"
    # ✅ Response indicates cancellation
    assert "cancel" in result["last_response"].lower() or "cancelled" in result["last_response"].lower()
```

#### Paso 3: Implementar test de cancellation durante confirmation

**Archivo(s) a modificar:** `tests/unit/test_dm_nodes_handle_cancellation.py`

**Código específico:**

```python
async def test_handle_cancellation_during_confirmation(
    create_state_with_flow, mock_runtime
):
    """User cancels during confirmation step."""
    # Arrange
    state = create_state_with_flow("book_flight")
    state["flow_stack"] = [{"flow_id": "flow_1", "flow_name": "book_flight"}]
    state["conversation_state"] = "confirming"
    state["nlu_result"] = {
        "message_type": MessageType.CANCELLATION.value,
    }

    mock_runtime.context["flow_manager"].get_active_context.return_value = {
        "flow_id": "flow_1",
        "flow_name": "book_flight",
    }

    def mock_pop_flow(state, result):
        state["flow_stack"].pop()

    mock_runtime.context["flow_manager"].pop_flow.side_effect = mock_pop_flow

    # Act
    result = await handle_cancellation_node(state, mock_runtime)

    # Assert
    assert result["conversation_state"] == "idle"
    assert len(result["flow_stack"]) == 0
```

#### Paso 4: Implementar test de pop a parent flow

**Archivo(s) a modificar:** `tests/unit/test_dm_nodes_handle_cancellation.py`

**Código específico:**

```python
async def test_handle_cancellation_pops_to_parent_flow(
    create_state_with_flow, mock_runtime
):
    """
    Cancellation with multiple flows in stack - returns to parent.

    Design Reference: docs/design/10-dsl-specification/06-patterns.md:20-48
    Pattern: "Returns to parent flow or idle state"
    """
    # Arrange
    state = create_state_with_flow("book_flight")
    state["flow_stack"] = [
        {"flow_id": "flow_1", "flow_name": "book_flight", "flow_state": "paused"},
        {"flow_id": "flow_2", "flow_name": "check_weather", "flow_state": "active"}  # Current
    ]
    state["nlu_result"] = {
        "message_type": MessageType.CANCELLATION.value,
    }

    mock_runtime.context["flow_manager"].get_active_context.return_value = {
        "flow_id": "flow_2",
        "flow_name": "check_weather",
    }

    def mock_pop_flow(state, result):
        # Pop current flow (flow_2)
        state["flow_stack"].pop()
        # Resume parent (flow_1)
        if state["flow_stack"]:
            state["flow_stack"][-1]["flow_state"] = "active"

    mock_runtime.context["flow_manager"].pop_flow.side_effect = mock_pop_flow

    # Act
    result = await handle_cancellation_node(state, mock_runtime)

    # Assert
    # ✅ Pop current flow, resume parent
    assert len(result["flow_stack"]) == 1
    assert result["flow_stack"][0]["flow_name"] == "book_flight"
    assert result["flow_stack"][0]["flow_state"] == "active"
```

#### Paso 5: Implementar tests adicionales

**Tests adicionales requeridos:**

1. `test_handle_cancellation_from_idle` - Cancellation sin active flow
2. `test_handle_cancellation_cleanup_metadata` - Limpieza de metadata
3. `test_handle_cancellation_during_action` - Cancellation durante ejecución de acción

### TDD Cycle (MANDATORY for new features)

#### Red Phase: Write Failing Tests

**Test file:** `tests/unit/test_dm_nodes_handle_cancellation.py`

**Failing tests to write FIRST:**

```python
# Test 1: Cancellation during slot collection
async def test_handle_cancellation_during_slot_collection(...):
    """Test that cancellation pops flow during slot collection."""
    # Arrange
    # Act
    # Assert
    pass  # Will fail until implemented

# Test 2: Cancellation during confirmation
async def test_handle_cancellation_during_confirmation(...):
    """Test that cancellation pops flow during confirmation."""
    # Arrange
    # Act
    # Assert
    pass  # Will fail until implemented

# Test 3: Pop to parent flow
async def test_handle_cancellation_pops_to_parent_flow(...):
    """Test that cancellation pops to parent when multiple flows exist."""
    # Arrange
    # Act
    # Assert
    pass  # Will fail until implemented
```

**Verify tests fail:**
```bash
uv run pytest tests/unit/test_dm_nodes_handle_cancellation.py -v
# Expected: Some tests may pass (node exists), but verify all scenarios
```

**Commit:**
```bash
git add tests/unit/test_dm_nodes_handle_cancellation.py
git commit -m "test: add tests for cancellation pattern"
```

#### Green Phase: Make Tests Pass

**Verify all tests pass with current implementation.**

Si algún test falla, puede requerir ajustes en el nodo `handle_cancellation_node`.

**Verify tests pass:**
```bash
uv run pytest tests/unit/test_dm_nodes_handle_cancellation.py -v
# Expected: PASSED ✅
```

**Commit:**
```bash
git add src/ tests/
git commit -m "feat: complete cancellation pattern tests"
```

#### Refactor Phase: Improve Design

**Refactor tests if needed while keeping them green.**

- Improve test readability
- Extract common setup to fixtures
- Add better assertions
- Tests must still pass!

**Commit:**
```bash
git add tests/
git commit -m "refactor: improve cancellation tests"
```

---

### Tests Requeridos

**Archivo de tests:** `tests/unit/test_dm_nodes_handle_cancellation.py`

**Tests específicos a implementar:**

```python
# Test 1: During slot collection
async def test_handle_cancellation_during_slot_collection():
    """User cancels while collecting slots."""
    # Arrange
    # Act
    # Assert
    # - Flow popped from stack
    # - Returns to idle
    # - Metadata cleaned

# Test 2: During confirmation
async def test_handle_cancellation_during_confirmation():
    """User cancels during confirmation."""
    # Arrange
    # Act
    # Assert
    # - Flow popped
    # - Returns to idle

# Test 3: Pop to parent flow
async def test_handle_cancellation_pops_to_parent_flow():
    """Cancellation with multiple flows returns to parent."""
    # Arrange
    # Act
    # Assert
    # - Current flow popped
    # - Parent flow resumed
    # - Correct flow_stack state

# Test 4: From idle
async def test_handle_cancellation_from_idle():
    """Cancellation when no active flow."""
    # Arrange
    # Act
    # Assert
    # - Graceful handling
    # - Appropriate message

# Test 5: Cleanup metadata
async def test_handle_cancellation_cleanup_metadata():
    """Cancellation cleans up metadata."""
    # Arrange
    # Act
    # Assert
    # - Metadata cleaned or preserved appropriately
```

### Criterios de Éxito

- [ ] Archivo `test_dm_nodes_handle_cancellation.py` creado
- [ ] Mínimo 5 tests implementados y pasando
- [ ] Tests cubren todos los escenarios: collect, confirm, action, idle, multi-flow
- [ ] Todos los tests usan fixtures de conftest.py
- [ ] Todos los tests siguen patrón AAA
- [ ] Cobertura del nodo >90%
- [ ] Linting pasa sin errores
- [ ] Type checking pasa sin errores

### Validación Manual

**Comandos para validar:**

```bash
# Run tests
uv run pytest tests/unit/test_dm_nodes_handle_cancellation.py -v

# Check coverage
uv run pytest tests/unit/test_dm_nodes_handle_cancellation.py --cov=src/soni/dm/nodes/handle_cancellation --cov-report=term-missing

# Linting
uv run ruff check tests/unit/test_dm_nodes_handle_cancellation.py

# Type checking
uv run mypy tests/unit/test_dm_nodes_handle_cancellation.py
```

**Resultado esperado:**
- Todos los tests pasan
- Cobertura >90% del nodo handle_cancellation
- Sin errores de linting o type checking

### Referencias

- `docs/analysis/INFORME_CONFORMIDAD_DISENO_TESTS.md` - Issue #2: Missing CANCELLATION Pattern Tests
- `docs/design/10-dsl-specification/06-patterns.md:20-48` - Especificación del patrón
- `src/soni/dm/nodes/handle_cancellation.py` - Implementación actual del nodo
- `docs/design/07-flow-management.md` - Gestión de flows y pop_flow
- `tests/unit/conftest.py` - Fixtures disponibles

### Notas Adicionales

- **Importante**: El nodo `handle_cancellation_node` ya existe, pero necesita tests exhaustivos.
- **Escenarios críticos**: Debe funcionar durante collect, confirm, action, y con múltiples flows en stack.
- **NLU Mocking**: Todos los tests deben mockear el NLU usando fixtures de `conftest.py`.
- **Design Reference**: Agregar comentarios con referencias al diseño en cada test.
- **Metadata cleanup**: Verificar si metadata debe limpiarse o preservarse según diseño.
