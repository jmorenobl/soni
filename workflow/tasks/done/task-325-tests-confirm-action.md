## Task: 325 - Tests Unitarios para confirm_action.py

**ID de tarea:** 325
**Hito:** Tests Unitarios - Cobertura >85% (Fase ALTA)
**Dependencias:** task-308-update-conftest-fixtures.md
**Duración estimada:** 1 día

### Objetivo

Implementar tests unitarios para `dm/nodes/confirm_action.py` para alcanzar cobertura >85%. Este módulo genera y muestra el mensaje de confirmación al usuario.

### Contexto

Según análisis de revisión (`docs/analysis/REVISION_TAREAS_BACKLOG_TESTS.md`):
- **Módulo identificado como faltante** en tareas originales
- **Prioridad**: ALTA - Componente crítico del patrón de confirmación
- **LOC**: 147 líneas
- **Tests estimados**: ~12-15 tests

El módulo `confirm_action.py` maneja:
- Construcción del mensaje de confirmación
- Interpolación de slots en plantilla de confirmación
- Manejo de slots faltantes en interpolación
- Primera ejecución (interrumpir para mostrar confirmación)
- Re-ejecución después de resumir (pasar through)
- Preservación de respuesta existente
- Flags de metadata (`_confirmation_processed`)

### Entregables

- [ ] Tests para construcción de mensaje de confirmación
- [ ] Tests para interpolación de slots
- [ ] Tests para manejo de slots faltantes
- [ ] Tests para primera ejecución vs re-ejecución
- [ ] Tests para preservación de respuesta
- [ ] Tests para flags de metadata
- [ ] Tests para edge cases (sin active flow, sin step, etc.)
- [ ] Cobertura >85% para el módulo
- [ ] Todos los tests pasan y son deterministas

### Implementación Detallada

#### Paso 1: Crear archivo de tests

**Archivo(s) a crear/modificar:** `tests/unit/test_dm_nodes_confirm_action.py`

**Estructura base:**

```python
"""
Unit tests for confirm_action node.

All tests use mocked state and runtime for determinism.
"""

import pytest
from unittest.mock import MagicMock
from soni.dm.nodes.confirm_action import confirm_action_node
```

#### Paso 2: Tests de construcción de confirmación

**Tests a implementar:**

```python
@pytest.mark.asyncio
async def test_confirm_action_builds_confirmation_message(
    create_state_with_slots,
    mock_runtime,
    mock_flow_config_complete
):
    """Test que confirm_action construye mensaje de confirmación."""
    # Arrange
    state = create_state_with_slots(
        "book_flight",
        slots={"origin": "Madrid", "destination": "Barcelona", "date": "2025-12-25"},
        current_step="confirm_booking",
        conversation_state="ready_for_confirmation"
    )

    # Mock step config con template de confirmación
    mock_step_config = MagicMock(
        step="confirm_booking",
        type="confirm",
        prompt="You want to fly from {origin} to {destination} on {date}, correct?"
    )
    mock_runtime.context["step_manager"].get_current_step_config.return_value = mock_step_config

    # Act
    result = await confirm_action_node(state, mock_runtime)

    # Assert
    assert "last_response" in result
    assert "Madrid" in result["last_response"]
    assert "Barcelona" in result["last_response"]
    assert "2025-12-25" in result["last_response"]


@pytest.mark.asyncio
async def test_confirm_action_interpolates_slots(
    create_state_with_slots,
    mock_runtime
):
    """Test que confirm_action interpola slots correctamente."""
    # Arrange
    state = create_state_with_slots(
        "book_flight",
        slots={"origin": "Madrid", "destination": "Barcelona"},
        current_step="confirm_booking"
    )

    mock_step_config = MagicMock(
        step="confirm_booking",
        type="confirm",
        prompt="Confirm: {origin} → {destination}?"
    )
    mock_runtime.context["step_manager"].get_current_step_config.return_value = mock_step_config

    # Act
    result = await confirm_action_node(state, mock_runtime)

    # Assert
    assert "Madrid" in result["last_response"]
    assert "Barcelona" in result["last_response"]
    assert "{origin}" not in result["last_response"]  # Placeholder reemplazado
    assert "{destination}" not in result["last_response"]  # Placeholder reemplazado


@pytest.mark.asyncio
async def test_confirm_action_missing_slot_in_interpolation(
    create_state_with_slots,
    mock_runtime
):
    """Test que confirm_action maneja slots faltantes en template."""
    # Arrange
    state = create_state_with_slots(
        "book_flight",
        slots={"origin": "Madrid"},  # Falta destination
        current_step="confirm_booking"
    )

    mock_step_config = MagicMock(
        step="confirm_booking",
        type="confirm",
        prompt="From {origin} to {destination}?"
    )
    mock_runtime.context["step_manager"].get_current_step_config.return_value = mock_step_config

    # Act
    result = await confirm_action_node(state, mock_runtime)

    # Assert - Puede dejar placeholder o usar valor default
    assert "Madrid" in result["last_response"]
    # El placeholder {destination} puede quedar sin reemplazar o usar default
    assert "{destination}" in result["last_response"] or "destination" not in result["last_response"].lower()


@pytest.mark.asyncio
async def test_confirm_action_no_slots_interpolated(
    create_state_with_flow,
    mock_runtime
):
    """Test que confirm_action funciona sin interpolación de slots."""
    # Arrange
    state = create_state_with_flow(
        "simple_flow",
        current_step="confirm_action"
    )

    mock_step_config = MagicMock(
        step="confirm_action",
        type="confirm",
        prompt="Are you sure you want to proceed?"  # No placeholders
    )
    mock_runtime.context["step_manager"].get_current_step_config.return_value = mock_step_config

    # Act
    result = await confirm_action_node(state, mock_runtime)

    # Assert
    assert result["last_response"] == "Are you sure you want to proceed?"
```

#### Paso 3: Tests de primera ejecución vs re-ejecución

**Tests a implementar:**

```python
@pytest.mark.asyncio
async def test_confirm_action_first_execution_interrupts(
    create_state_with_slots,
    mock_runtime
):
    """Test que primera ejecución de confirm_action interrumpe flujo."""
    # Arrange
    state = create_state_with_slots(
        "book_flight",
        slots={"origin": "Madrid", "destination": "Barcelona"},
        current_step="confirm_booking",
        metadata={}  # No _confirmation_processed flag
    )

    mock_step_config = MagicMock(
        step="confirm_booking",
        type="confirm",
        prompt="Confirm?"
    )
    mock_runtime.context["step_manager"].get_current_step_config.return_value = mock_step_config

    # Act
    result = await confirm_action_node(state, mock_runtime)

    # Assert - Primera ejecución debe generar response y setear flag
    assert "last_response" in result
    # Metadata debe indicar que ya se procesó
    assert result.get("metadata", {}).get("_confirmation_processed") is True


@pytest.mark.asyncio
async def test_confirm_action_re_execution_after_resume(
    create_state_with_slots,
    mock_runtime
):
    """Test que re-ejecución después de resumir pasa through."""
    # Arrange
    state = create_state_with_slots(
        "book_flight",
        slots={"origin": "Madrid"},
        current_step="confirm_booking",
        metadata={"_confirmation_processed": True}  # Ya procesado
    )

    mock_step_config = MagicMock(
        step="confirm_booking",
        type="confirm",
        prompt="Confirm?"
    )
    mock_runtime.context["step_manager"].get_current_step_config.return_value = mock_step_config

    # Act
    result = await confirm_action_node(state, mock_runtime)

    # Assert - Re-ejecución debe pasar through sin interrumpir
    assert result == {} or "_confirmation_processed" not in result.get("metadata", {})


@pytest.mark.asyncio
async def test_confirm_action_preserves_existing_response(
    create_state_with_slots,
    mock_runtime
):
    """Test que confirm_action preserva respuesta existente en re-ejecución."""
    # Arrange
    state = create_state_with_slots(
        "book_flight",
        slots={"origin": "Madrid"},
        current_step="confirm_booking",
        metadata={"_confirmation_processed": True}
    )
    state["last_response"] = "Previous response"

    mock_step_config = MagicMock(
        step="confirm_booking",
        type="confirm",
        prompt="New prompt"
    )
    mock_runtime.context["step_manager"].get_current_step_config.return_value = mock_step_config

    # Act
    result = await confirm_action_node(state, mock_runtime)

    # Assert - No debe sobrescribir last_response existente
    assert "last_response" not in result or result["last_response"] == "Previous response"
```

#### Paso 4: Tests de edge cases

**Tests a implementar:**

```python
@pytest.mark.asyncio
async def test_confirm_action_no_active_flow(
    mock_runtime
):
    """Test que confirm_action maneja ausencia de flow activo."""
    # Arrange
    from soni.core.state import create_empty_state
    state = create_empty_state()

    mock_runtime.context["flow_manager"].get_active_context.return_value = None

    # Act
    result = await confirm_action_node(state, mock_runtime)

    # Assert - Debe manejar gracefully
    assert result == {} or result.get("conversation_state") == "error"


@pytest.mark.asyncio
async def test_confirm_action_not_confirm_step(
    create_state_with_flow,
    mock_runtime
):
    """Test que confirm_action maneja step que no es de tipo confirm."""
    # Arrange
    state = create_state_with_flow(
        "book_flight",
        current_step="collect_origin"  # No es confirm step
    )

    mock_step_config = MagicMock(
        step="collect_origin",
        type="collect",  # No es confirm
        slot="origin"
    )
    mock_runtime.context["step_manager"].get_current_step_config.return_value = mock_step_config

    # Act
    result = await confirm_action_node(state, mock_runtime)

    # Assert - Debe pasar through o manejar gracefully
    assert result == {} or "conversation_state" not in result


@pytest.mark.asyncio
async def test_confirm_action_adds_slots_manually(
    create_state_with_slots,
    mock_runtime
):
    """Test que confirm_action puede agregar slots manualmente si no están en template."""
    # Arrange
    state = create_state_with_slots(
        "book_flight",
        slots={"origin": "Madrid", "destination": "Barcelona", "date": "2025-12-25"},
        current_step="confirm_booking"
    )

    mock_step_config = MagicMock(
        step="confirm_booking",
        type="confirm",
        prompt="Confirm your booking?"  # Sin placeholders
    )
    mock_runtime.context["step_manager"].get_current_step_config.return_value = mock_step_config

    # Act
    result = await confirm_action_node(state, mock_runtime)

    # Assert - Puede agregar slots como lista después del mensaje
    assert "last_response" in result
    # La respuesta puede incluir slots de alguna forma
    assert len(result["last_response"]) > 0
```

### Tests Requeridos

**Archivo de tests:** `tests/unit/test_dm_nodes_confirm_action.py`

**Tests específicos (checklist completo):**

- [ ] **Construcción de confirmación**
  - [ ] test_confirm_action_builds_confirmation_message
  - [ ] test_confirm_action_interpolates_slots
  - [ ] test_confirm_action_missing_slot_in_interpolation
  - [ ] test_confirm_action_no_slots_interpolated
  - [ ] test_confirm_action_adds_slots_manually

- [ ] **Primera ejecución vs re-ejecución**
  - [ ] test_confirm_action_first_execution_interrupts
  - [ ] test_confirm_action_re_execution_after_resume
  - [ ] test_confirm_action_preserves_existing_response
  - [ ] test_confirm_action_confirmation_processed_flag
  - [ ] test_confirm_action_passes_through_first_re_execution

- [ ] **Edge cases**
  - [ ] test_confirm_action_no_active_flow
  - [ ] test_confirm_action_not_confirm_step

**Total estimado**: ~12 tests

### Criterios de Éxito

- [ ] Todos los tests pasan (100% pass rate)
- [ ] Cobertura >85% para `dm/nodes/confirm_action.py`
- [ ] Todos los tests son deterministas
- [ ] Tests verifican interpolación de slots
- [ ] Tests verifican comportamiento de primera vs re-ejecución
- [ ] Linting pasa sin errores
- [ ] Type checking pasa sin errores
- [ ] Tests ejecutan en <1 segundo cada uno

### Validación Manual

**Comandos para validar:**

```bash
# Ejecutar tests del módulo
uv run pytest tests/unit/test_dm_nodes_confirm_action.py -v

# Verificar cobertura específica
uv run pytest tests/unit/test_dm_nodes_confirm_action.py \
    --cov=src/soni/dm/nodes/confirm_action \
    --cov-report=term-missing

# Verificar velocidad
uv run pytest tests/unit/test_dm_nodes_confirm_action.py --durations=10

# Verificar independencia
uv run pytest tests/unit/test_dm_nodes_confirm_action.py --random-order
```

**Resultado esperado:**
- Cobertura >85% para confirm_action.py
- Todos los tests pasan
- Tiempo de ejecución <15 segundos para todos los tests

### Referencias

- `docs/analysis/REVISION_TAREAS_BACKLOG_TESTS.md` - Sección 5.2
- `docs/analysis/ANALISIS_TESTS_UNITARIOS_COBERTURA.md` - Sección 2.4.5
- `docs/analysis/GUIA_IMPLEMENTACION_TESTS_UNITARIOS.md` - Sección 2
- `src/soni/dm/nodes/confirm_action.py` - Código fuente

### Notas Adicionales

- **CRÍTICO**: Verificar lógica de interrupciones con Command.WAIT
- Enfocarse en interpolación de slots con diferentes formatos
- Probar comportamiento de re-ejecución exhaustivamente
- Verificar que metadata flags se setean y limpian correctamente
- Asegurar que mensajes de confirmación son claros y completos
