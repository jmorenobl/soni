## Task: 309 - Tests Unitarios para handle_correction.py

**ID de tarea:** 309
**Hito:** Tests Unitarios - Cobertura >85% (Fase CRÍTICA)
**Dependencias:** task-308-update-conftest-fixtures.md
**Duración estimada:** 1-2 días

### Objetivo

Implementar tests unitarios exhaustivos para `dm/nodes/handle_correction.py` para alcanzar cobertura >85% (actualmente 6%). Todos los tests deben ser deterministas usando NLU mockeado.

### Contexto

Según `docs/analysis/ANALISIS_TESTS_UNITARIOS_COBERTURA.md`:
- **Cobertura actual**: 6%
- **Gap**: 79%
- **LOC**: 267 líneas
- **Tests estimados**: ~30 tests
- **Prioridad**: CRÍTICA - Patrón conversacional fundamental

El módulo `handle_correction.py` maneja correcciones de slots durante la conversación, incluyendo:
- Actualización de valores de slots
- Routing post-corrección a diferentes steps
- Manejo de metadata flags
- Generación de mensajes de acknowledgment

### Entregables

- [ ] Tests para formatos de slots (SlotValue object, dict format, unknown format)
- [ ] Tests para edge cases (sin NLU result, sin slots, sin active flow, normalization failure)
- [ ] Tests para routing post-corrección (collect, confirmation, action steps)
- [ ] Tests para estados previos (ready_for_action, ready_for_confirmation, confirming, waiting_for_slot)
- [ ] Tests para metadata y response (flags, acknowledgment messages, templates)
- [ ] Tests para función helper `_get_response_template`
- [ ] Cobertura >85% para el módulo
- [ ] Todos los tests pasan y son deterministas

### Implementación Detallada

#### Paso 1: Crear archivo de tests

**Archivo(s) a crear/modificar:** `tests/unit/test_dm_nodes_handle_correction.py`

**Estructura base:**

```python
"""
Unit tests for handle_correction node.

All tests use mocked NLU for determinism.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock
from soni.dm.nodes.handle_correction import handle_correction_node, _get_response_template
from soni.du.models import MessageType, SlotValue
```

#### Paso 2: Tests de formatos de slots

**Tests a implementar:**

```python
@pytest.mark.asyncio
async def test_handle_correction_slotvalue_format(
    create_state_with_slots,
    mock_nlu_correction,
    mock_runtime
):
    """Test que handle_correction maneja SlotValue object format."""
    # Arrange
    state = create_state_with_slots(
        "book_flight",
        slots={"destination": "Madrid"},
        current_step="collect_date"
    )
    # Mock NLU con SlotValue format
    nlu_result = mock_nlu_correction.predict.return_value
    state["nlu_result"] = nlu_result.model_dump()

    mock_runtime.context["normalizer"].normalize_slot.return_value = "Barcelona"

    # Act
    result = await handle_correction_node(state, mock_runtime)

    # Assert
    assert result["flow_slots"]["flow_1"]["destination"] == "Barcelona"
    assert result["metadata"]["_correction_slot"] == "destination"


@pytest.mark.asyncio
async def test_handle_correction_dict_format(
    create_state_with_slots,
    create_nlu_mock,
    mock_runtime
):
    """Test que handle_correction maneja dict format."""
    # Arrange
    state = create_state_with_slots(
        "book_flight",
        slots={"destination": "Madrid"}
    )
    # Mock NLU result como dict
    state["nlu_result"] = {
        "message_type": "correction",
        "command": "continue",
        "slots": [{"name": "destination", "value": "Barcelona"}],
        "confidence": 0.95
    }

    mock_runtime.context["normalizer"].normalize_slot.return_value = "Barcelona"

    # Act
    result = await handle_correction_node(state, mock_runtime)

    # Assert
    assert result["flow_slots"]["flow_1"]["destination"] == "Barcelona"


@pytest.mark.asyncio
async def test_handle_correction_unknown_format(
    create_state_with_slots,
    mock_runtime
):
    """Test que handle_correction maneja formato desconocido."""
    # Arrange
    state = create_state_with_slots("book_flight", slots={"origin": "Madrid"})
    state["nlu_result"] = {
        "message_type": "correction",
        "slots": [{"invalid": "format"}]  # Formato desconocido
    }

    # Act
    result = await handle_correction_node(state, mock_runtime)

    # Assert
    assert result.get("conversation_state") == "error"
```

#### Paso 3: Tests de edge cases

**Tests a implementar:**

```python
@pytest.mark.asyncio
async def test_handle_correction_no_nlu_result(
    create_state_with_slots,
    mock_runtime
):
    """Test que handle_correction maneja ausencia de NLU result."""
    # Arrange
    state = create_state_with_slots("book_flight", slots={"origin": "Madrid"})
    state["nlu_result"] = None

    # Act
    result = await handle_correction_node(state, mock_runtime)

    # Assert
    assert result.get("conversation_state") == "error"


@pytest.mark.asyncio
async def test_handle_correction_no_slots(
    create_state_with_slots,
    mock_runtime
):
    """Test que handle_correction maneja ausencia de slots en NLU."""
    # Arrange
    state = create_state_with_slots("book_flight", slots={"origin": "Madrid"})
    state["nlu_result"] = {
        "message_type": "correction",
        "slots": []  # Sin slots
    }

    # Act
    result = await handle_correction_node(state, mock_runtime)

    # Assert
    assert result.get("conversation_state") == "error"


@pytest.mark.asyncio
async def test_handle_correction_no_active_flow(
    create_nlu_mock,
    mock_runtime
):
    """Test que handle_correction maneja ausencia de flow activo."""
    # Arrange
    from soni.core.state import create_empty_state
    state = create_empty_state()
    state["nlu_result"] = create_nlu_mock(MessageType.CORRECTION).predict.return_value.model_dump()

    # Act
    result = await handle_correction_node(state, mock_runtime)

    # Assert
    assert result.get("conversation_state") == "error"


@pytest.mark.asyncio
async def test_handle_correction_normalization_failure(
    create_state_with_slots,
    mock_nlu_correction,
    mock_normalizer_failure
):
    """Test que handle_correction maneja fallo de normalización."""
    # Arrange
    state = create_state_with_slots("book_flight", slots={"destination": "Madrid"})
    state["nlu_result"] = mock_nlu_correction.predict.return_value.model_dump()

    mock_runtime = MagicMock()
    mock_runtime.context = {
        "normalizer": mock_normalizer_failure,
        "flow_manager": MagicMock(),
        "step_manager": MagicMock(),
        "config": MagicMock()
    }

    # Act
    result = await handle_correction_node(state, mock_runtime)

    # Assert
    assert result.get("conversation_state") == "error"
```

#### Paso 4: Tests de routing post-corrección

**Tests a implementar:**

```python
@pytest.mark.asyncio
async def test_handle_correction_returns_to_collect_step(
    create_state_with_slots,
    mock_nlu_correction,
    mock_runtime
):
    """Test que corrección durante collection vuelve a collect step."""
    # Arrange
    state = create_state_with_slots(
        "book_flight",
        slots={"origin": "Madrid"},
        current_step="collect_destination",
        conversation_state="waiting_for_slot"
    )
    state["nlu_result"] = mock_nlu_correction.predict.return_value.model_dump()
    state["metadata"]["_previous_state"] = "waiting_for_slot"

    mock_runtime.context["normalizer"].normalize_slot.return_value = "Barcelona"
    mock_runtime.context["step_manager"].get_current_step_config.return_value = {
        "step": "collect_destination",
        "type": "collect"
    }

    # Act
    result = await handle_correction_node(state, mock_runtime)

    # Assert
    assert result["conversation_state"] == "waiting_for_slot"
    assert result["flow_stack"][0]["current_step"] == "collect_destination"


@pytest.mark.asyncio
async def test_handle_correction_returns_to_confirmation_step(
    create_state_with_slots,
    mock_nlu_correction,
    mock_runtime
):
    """Test que corrección durante confirmation vuelve a confirmation step."""
    # Arrange
    state = create_state_with_slots(
        "book_flight",
        slots={"origin": "Madrid", "destination": "Barcelona"},
        current_step="confirm_booking",
        conversation_state="confirming"
    )
    state["nlu_result"] = mock_nlu_correction.predict.return_value.model_dump()
    state["metadata"]["_previous_state"] = "ready_for_confirmation"

    mock_runtime.context["normalizer"].normalize_slot.return_value = "Valencia"

    # Act
    result = await handle_correction_node(state, mock_runtime)

    # Assert
    assert result["conversation_state"] == "ready_for_confirmation"
    assert result["flow_stack"][0]["current_step"] == "confirm_booking"


@pytest.mark.asyncio
async def test_handle_correction_all_slots_filled_routes_to_confirmation(
    create_state_with_slots,
    mock_nlu_correction,
    mock_runtime
):
    """Test que corrección con todos los slots llenos va a confirmation."""
    # Arrange
    state = create_state_with_slots(
        "book_flight",
        slots={"origin": "Madrid", "destination": "Barcelona", "date": "2025-12-25"},
        current_step="collect_date"
    )
    state["nlu_result"] = mock_nlu_correction.predict.return_value.model_dump()

    # Mock que todos los slots están llenos
    mock_runtime.context["flow_manager"].get_active_context.return_value = {
        "flow_id": "flow_1",
        "flow_name": "book_flight",
        "current_step": "collect_date"
    }

    # Act
    result = await handle_correction_node(state, mock_runtime)

    # Assert
    # Debe avanzar a confirmation si todos los slots están llenos
    assert result["conversation_state"] in ["ready_for_confirmation", "waiting_for_slot"]
```

#### Paso 5: Tests de metadata y response

**Tests a implementar:**

```python
@pytest.mark.asyncio
async def test_handle_correction_sets_metadata_flags(
    create_state_with_slots,
    mock_nlu_correction,
    mock_runtime
):
    """Test que handle_correction setea flags de metadata correctamente."""
    # Arrange
    state = create_state_with_slots("book_flight", slots={"destination": "Madrid"})
    state["nlu_result"] = mock_nlu_correction.predict.return_value.model_dump()

    mock_runtime.context["normalizer"].normalize_slot.return_value = "Barcelona"

    # Act
    result = await handle_correction_node(state, mock_runtime)

    # Assert
    assert result["metadata"]["_correction_slot"] == "destination"
    assert result["metadata"]["_correction_value"] == "Barcelona"
    assert "_modification_slot" not in result["metadata"]  # Debe limpiar modification


@pytest.mark.asyncio
async def test_handle_correction_clears_modification_flags(
    create_state_with_slots,
    mock_nlu_correction,
    mock_runtime
):
    """Test que handle_correction limpia flags de modification."""
    # Arrange
    state = create_state_with_slots("book_flight", slots={"destination": "Madrid"})
    state["metadata"]["_modification_slot"] = "origin"
    state["nlu_result"] = mock_nlu_correction.predict.return_value.model_dump()

    mock_runtime.context["normalizer"].normalize_slot.return_value = "Barcelona"

    # Act
    result = await handle_correction_node(state, mock_runtime)

    # Assert
    assert "_modification_slot" not in result["metadata"]


@pytest.mark.asyncio
async def test_handle_correction_acknowledgment_message(
    create_state_with_slots,
    mock_nlu_correction,
    mock_runtime
):
    """Test que handle_correction genera mensaje de acknowledgment."""
    # Arrange
    state = create_state_with_slots("book_flight", slots={"destination": "Madrid"})
    state["nlu_result"] = mock_nlu_correction.predict.return_value.model_dump()

    mock_runtime.context["normalizer"].normalize_slot.return_value = "Barcelona"

    # Act
    result = await handle_correction_node(state, mock_runtime)

    # Assert
    assert "last_response" in result
    assert len(result["last_response"]) > 0
    # Mensaje debe contener acknowledgment
    assert any(word in result["last_response"].lower() for word in ["updated", "changed", "corrected", "got it"])
```

#### Paso 6: Tests de _get_response_template

**Tests a implementar:**

```python
def test_get_response_template_from_config_dict():
    """Test que _get_response_template obtiene template de config dict."""
    # Arrange
    config = MagicMock()
    config.responses = {
        "correction_acknowledgment": {
            "template": "Updated {slot} to {value}"
        }
    }

    # Act
    result = _get_response_template(
        config,
        "correction_acknowledgment",
        "Default message",
        slot="destination",
        value="Barcelona"
    )

    # Assert
    assert "destination" in result
    assert "Barcelona" in result


def test_get_response_template_default_fallback():
    """Test que _get_response_template usa default si no hay config."""
    # Arrange
    config = MagicMock()
    config.responses = {}

    # Act
    result = _get_response_template(
        config,
        "correction_acknowledgment",
        "Default message"
    )

    # Assert
    assert result == "Default message"


def test_get_response_template_interpolation():
    """Test que _get_response_template interpola variables correctamente."""
    # Arrange
    config = MagicMock()
    config.responses = {
        "correction_acknowledgment": {
            "template": "Updated {slot} from {old_value} to {new_value}"
        }
    }

    # Act
    result = _get_response_template(
        config,
        "correction_acknowledgment",
        "Default",
        slot="destination",
        old_value="Madrid",
        new_value="Barcelona"
    )

    # Assert
    assert "destination" in result
    assert "Madrid" in result
    assert "Barcelona" in result
```

### Tests Requeridos

**Archivo de tests:** `tests/unit/test_dm_nodes_handle_correction.py`

**Tests específicos a implementar (checklist completo):**

- [ ] **Formatos de slots**
  - [ ] test_handle_correction_slotvalue_format
  - [ ] test_handle_correction_dict_format
  - [ ] test_handle_correction_unknown_format

- [ ] **Edge cases**
  - [ ] test_handle_correction_no_nlu_result
  - [ ] test_handle_correction_no_slots
  - [ ] test_handle_correction_no_active_flow
  - [ ] test_handle_correction_normalization_failure

- [ ] **Routing post-corrección**
  - [ ] test_handle_correction_returns_to_collect_step
  - [ ] test_handle_correction_returns_to_confirmation_step
  - [ ] test_handle_correction_returns_to_action_step
  - [ ] test_handle_correction_all_slots_filled_routes_to_confirmation
  - [ ] test_handle_correction_all_slots_filled_routes_to_action
  - [ ] test_handle_correction_partial_slots_routes_to_collect

- [ ] **Estados previos**
  - [ ] test_handle_correction_from_ready_for_action
  - [ ] test_handle_correction_from_ready_for_confirmation
  - [ ] test_handle_correction_from_confirming
  - [ ] test_handle_correction_from_waiting_for_slot

- [ ] **Metadata y response**
  - [ ] test_handle_correction_sets_metadata_flags
  - [ ] test_handle_correction_clears_modification_flags
  - [ ] test_handle_correction_acknowledgment_message
  - [ ] test_handle_correction_response_template_from_config
  - [ ] test_handle_correction_response_template_default

- [ ] **_get_response_template**
  - [ ] test_get_response_template_from_config_dict
  - [ ] test_get_response_template_from_config_string
  - [ ] test_get_response_template_default_fallback
  - [ ] test_get_response_template_interpolation_single_var
  - [ ] test_get_response_template_interpolation_multiple_vars
  - [ ] test_get_response_template_missing_config

**Total estimado**: ~30 tests

### Criterios de Éxito

- [ ] Todos los tests pasan (100% pass rate)
- [ ] Cobertura >85% para `dm/nodes/handle_correction.py`
- [ ] Todos los tests son deterministas (NLU mockeado)
- [ ] Tests siguen patrón AAA (Arrange-Act-Assert)
- [ ] Todos los tests tienen docstrings descriptivos
- [ ] Linting pasa sin errores
- [ ] Type checking pasa sin errores
- [ ] Tests ejecutan en <1 segundo cada uno

### Validación Manual

**Comandos para validar:**

```bash
# Ejecutar tests del módulo
uv run pytest tests/unit/test_dm_nodes_handle_correction.py -v

# Verificar cobertura específica
uv run pytest tests/unit/test_dm_nodes_handle_correction.py \
    --cov=src/soni/dm/nodes/handle_correction \
    --cov-report=term-missing

# Verificar velocidad
uv run pytest tests/unit/test_dm_nodes_handle_correction.py --durations=10

# Verificar independencia (orden aleatorio)
uv run pytest tests/unit/test_dm_nodes_handle_correction.py --random-order
```

**Resultado esperado:**
- Cobertura >85% para handle_correction.py
- Todos los tests pasan
- Tiempo de ejecución <30 segundos para todos los tests

### Referencias

- `docs/analysis/ANALISIS_TESTS_UNITARIOS_COBERTURA.md` - Sección 2.1
- `docs/analysis/GUIA_IMPLEMENTACION_TESTS_UNITARIOS.md` - Sección 2.1 y 3.1
- `src/soni/dm/nodes/handle_correction.py` - Código fuente

### Notas Adicionales

- **CRÍTICO**: Todos los tests deben mockear NLU (nunca usar LLM real)
- Usar fixtures de conftest.py (task-308)
- Seguir exactamente el checklist de la sección 3.1 de la guía
- Verificar que routing post-corrección funciona para todos los casos posibles
- Asegurar que metadata flags se setean/limpian correctamente
