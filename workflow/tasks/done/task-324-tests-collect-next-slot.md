## Task: 324 - Tests Unitarios para collect_next_slot.py

**ID de tarea:** 324
**Hito:** Tests Unitarios - Cobertura >85% (Fase ALTA)
**Dependencias:** task-308-update-conftest-fixtures.md
**Duración estimada:** 1 día

### Objetivo

Implementar tests unitarios para `dm/nodes/collect_next_slot.py` para alcanzar cobertura >85%. Este módulo maneja la lógica de colección del siguiente slot en el flujo.

### Contexto

Según análisis de revisión (`docs/analysis/REVISION_TAREAS_BACKLOG_TESTS.md`):
- **Módulo identificado como faltante** en tareas originales
- **Prioridad**: ALTA - Componente crítico de colección de slots
- **LOC**: 93 líneas
- **Tests estimados**: ~8-10 tests

El módulo `collect_next_slot.py` maneja:
- Avanzar al siguiente slot no lleno
- Obtener configuración del slot actual
- Generar prompt para el slot
- Interrumpir flujo para solicitar input del usuario
- Manejar re-ejecución después de resumir

### Entregables

- [ ] Tests para flujo normal de colección de siguiente slot
- [ ] Tests para casos cuando no hay siguiente slot
- [ ] Tests para obtención de configuración de slot
- [ ] Tests para generación de prompts
- [ ] Tests para interrupciones y re-ejecuciones
- [ ] Tests para edge cases (sin active flow, sin current step, etc.)
- [ ] Cobertura >85% para el módulo
- [ ] Todos los tests pasan y son deterministas

### Implementación Detallada

#### Paso 1: Crear archivo de tests

**Archivo(s) a crear/modificar:** `tests/unit/test_dm_nodes_collect_next_slot.py`

**Estructura base:**

```python
"""
Unit tests for collect_next_slot node.

All tests use mocked NLU for determinism.
"""

import pytest
from unittest.mock import MagicMock
from soni.dm.nodes.collect_next_slot import collect_next_slot_node
```

#### Paso 2: Tests de flujo normal

**Tests a implementar:**

```python
@pytest.mark.asyncio
async def test_collect_next_slot_gets_slot_config(
    create_state_with_flow,
    mock_runtime,
    mock_flow_config_complete
):
    """Test que collect_next_slot obtiene configuración del slot."""
    # Arrange
    state = create_state_with_flow(
        "book_flight",
        current_step="collect_origin",
        conversation_state="waiting_for_slot"
    )

    # Mock step_manager para retornar step config
    mock_runtime.context["step_manager"].get_current_step_config.return_value = MagicMock(
        step="collect_origin",
        type="collect",
        slot="origin",
        prompt="Where are you flying from?"
    )

    mock_runtime.context["step_manager"].config.flows = {
        "book_flight": mock_flow_config_complete
    }

    # Act
    result = await collect_next_slot_node(state, mock_runtime)

    # Assert
    assert "last_response" in result
    assert "from" in result["last_response"].lower() or "origin" in result["last_response"].lower()


@pytest.mark.asyncio
async def test_collect_next_slot_interrupts_with_prompt(
    create_state_with_flow,
    mock_runtime
):
    """Test que collect_next_slot interrumpe flujo para solicitar input."""
    # Arrange
    state = create_state_with_flow(
        "book_flight",
        current_step="collect_destination"
    )

    mock_runtime.context["step_manager"].get_current_step_config.return_value = MagicMock(
        step="collect_destination",
        type="collect",
        slot="destination",
        prompt="Where would you like to go?"
    )

    # Act
    result = await collect_next_slot_node(state, mock_runtime)

    # Assert - Primera ejecución debe interrumpir
    # (El comportamiento exacto depende de la implementación con Command.WAIT)
    assert "last_response" in result or "conversation_state" in result


@pytest.mark.asyncio
async def test_collect_next_slot_re_execution_after_resume(
    create_state_with_flow,
    mock_runtime
):
    """Test que collect_next_slot maneja re-ejecución después de resumir."""
    # Arrange
    state = create_state_with_flow(
        "book_flight",
        current_step="collect_origin",
        metadata={"_collect_slot_executed": True}  # Ya ejecutado antes
    )

    mock_runtime.context["step_manager"].get_current_step_config.return_value = MagicMock(
        step="collect_origin",
        type="collect",
        slot="origin",
        prompt="Where?"
    )

    # Act
    result = await collect_next_slot_node(state, mock_runtime)

    # Assert - Segunda ejecución debe pasar through sin interrumpir
    assert result == {} or "conversation_state" in result
```

#### Paso 3: Tests de edge cases

**Tests a implementar:**

```python
@pytest.mark.asyncio
async def test_collect_next_slot_no_active_flow(
    mock_runtime
):
    """Test que collect_next_slot maneja ausencia de flow activo."""
    # Arrange
    from soni.core.state import create_empty_state
    state = create_empty_state()

    mock_runtime.context["flow_manager"].get_active_context.return_value = None

    # Act
    result = await collect_next_slot_node(state, mock_runtime)

    # Assert - Debe manejar gracefully
    assert result == {} or result.get("conversation_state") == "error"


@pytest.mark.asyncio
async def test_collect_next_slot_no_current_step_advances(
    create_state_with_flow,
    mock_runtime
):
    """Test que collect_next_slot avanza si no hay current_step."""
    # Arrange
    state = create_state_with_flow("book_flight")
    state["flow_stack"][0]["current_step"] = None  # No current step

    # Mock step_manager para avanzar
    mock_runtime.context["step_manager"].advance_to_next_step.return_value = {
        "flow_stack": [{"current_step": "collect_origin"}],
        "conversation_state": "waiting_for_slot"
    }

    # Act
    result = await collect_next_slot_node(state, mock_runtime)

    # Assert - Debe avanzar a siguiente step
    assert mock_runtime.context["step_manager"].advance_to_next_step.called


@pytest.mark.asyncio
async def test_collect_next_slot_slot_config_not_found(
    create_state_with_flow,
    mock_runtime
):
    """Test que collect_next_slot maneja slot config no encontrado."""
    # Arrange
    state = create_state_with_flow(
        "book_flight",
        current_step="collect_invalid_slot"
    )

    # Mock step_manager para retornar None
    mock_runtime.context["step_manager"].get_current_step_config.return_value = None

    # Act
    result = await collect_next_slot_node(state, mock_runtime)

    # Assert - Debe manejar gracefully
    assert result == {} or result.get("conversation_state") in ("error", "waiting_for_slot")


@pytest.mark.asyncio
async def test_collect_next_slot_no_next_slot_advances_step(
    create_state_with_slots,
    mock_runtime
):
    """Test que collect_next_slot avanza step si no hay siguiente slot."""
    # Arrange - Todos los slots ya llenos
    state = create_state_with_slots(
        "book_flight",
        slots={"origin": "Madrid", "destination": "Barcelona", "date": "2025-12-25"},
        current_step="collect_date"
    )

    # Mock: no hay siguiente slot no lleno
    mock_runtime.context["step_manager"].advance_to_next_step.return_value = {
        "flow_stack": [{"current_step": "confirm_booking"}],
        "conversation_state": "ready_for_confirmation"
    }

    # Act
    result = await collect_next_slot_node(state, mock_runtime)

    # Assert - Debe avanzar a confirmation
    assert result.get("conversation_state") in ("ready_for_confirmation", "waiting_for_slot")
```

### Tests Requeridos

**Archivo de tests:** `tests/unit/test_dm_nodes_collect_next_slot.py`

**Tests específicos (checklist completo):**

- [ ] **Flujo normal**
  - [ ] test_collect_next_slot_gets_slot_config
  - [ ] test_collect_next_slot_interrupts_with_prompt
  - [ ] test_collect_next_slot_re_execution_after_resume

- [ ] **Edge cases**
  - [ ] test_collect_next_slot_no_active_flow
  - [ ] test_collect_next_slot_no_current_step_advances
  - [ ] test_collect_next_slot_no_current_step_no_next_step
  - [ ] test_collect_next_slot_slot_config_not_found
  - [ ] test_collect_next_slot_no_next_slot_advances_step

**Total estimado**: ~8-10 tests

### Criterios de Éxito

- [ ] Todos los tests pasan (100% pass rate)
- [ ] Cobertura >85% para `dm/nodes/collect_next_slot.py`
- [ ] Todos los tests son deterministas (sin dependencias externas)
- [ ] Tests siguen patrón AAA (Arrange-Act-Assert)
- [ ] Todos los tests tienen docstrings descriptivos
- [ ] Linting pasa sin errores
- [ ] Type checking pasa sin errores
- [ ] Tests ejecutan en <1 segundo cada uno

### Validación Manual

**Comandos para validar:**

```bash
# Ejecutar tests del módulo
uv run pytest tests/unit/test_dm_nodes_collect_next_slot.py -v

# Verificar cobertura específica
uv run pytest tests/unit/test_dm_nodes_collect_next_slot.py \
    --cov=src/soni/dm/nodes/collect_next_slot \
    --cov-report=term-missing

# Verificar velocidad
uv run pytest tests/unit/test_dm_nodes_collect_next_slot.py --durations=10

# Verificar independencia (orden aleatorio)
uv run pytest tests/unit/test_dm_nodes_collect_next_slot.py --random-order
```

**Resultado esperado:**
- Cobertura >85% para collect_next_slot.py
- Todos los tests pasan
- Tiempo de ejecución <10 segundos para todos los tests

### Referencias

- `docs/analysis/REVISION_TAREAS_BACKLOG_TESTS.md` - Sección 5.2
- `docs/analysis/GUIA_IMPLEMENTACION_TESTS_UNITARIOS.md` - Sección 2
- `src/soni/dm/nodes/collect_next_slot.py` - Código fuente

### Notas Adicionales

- **CRÍTICO**: Todos los tests deben mockear dependencias (step_manager, flow_manager)
- Enfocarse en lógica de interrupciones con Command.WAIT
- Verificar comportamiento de re-ejecución
- Asegurar que prompts se generan correctamente
