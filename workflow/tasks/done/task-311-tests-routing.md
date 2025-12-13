## Task: 311 - Tests Unitarios para routing.py

**ID de tarea:** 311
**Hito:** Tests Unitarios - Cobertura >85% (Fase CRÍTICA)
**Dependencias:** task-308-update-conftest-fixtures.md
**Duración estimada:** 2-3 días

### Objetivo

Implementar tests unitarios exhaustivos para `dm/routing.py` para alcanzar cobertura >85% (actualmente 38%). Este módulo es crítico ya que controla todo el flujo de routing.

### Contexto

Según `docs/analysis/ANALISIS_TESTS_UNITARIOS_COBERTURA.md`:
- **Cobertura actual**: 38%
- **Gap**: 47%
- **LOC**: 661 líneas
- **Tests estimados**: ~50-60 tests
- **Prioridad**: CRÍTICA - Control de flujo de toda la aplicación

El módulo `routing.py` contiene múltiples funciones de routing:
- `route_after_understand()` - Routing después de NLU
- `route_after_validate()` - Routing después de validación
- `route_after_correction()` - Routing después de corrección
- `route_after_modification()` - Routing después de modificación
- `route_after_collect_next_slot()` - Routing después de colección
- `route_after_action()` - Routing después de acción
- `route_after_confirmation()` - Routing después de confirmación
- `should_continue_flow()` - Verificar si flow debe continuar
- `activate_flow_by_intent()` - Activar flow por intent
- `create_branch_router()` - Crear router de branches

### ⚠️ IMPORTANTE: Tests Existentes Fallando

Antes de agregar nuevos tests, **ARREGLAR** los siguientes 4 tests que están fallando:

```bash
# Tests que actualmente fallan (verificado en reporte de cobertura)
FAILED tests/unit/test_routing.py::test_route_after_validate_warns_unexpected_state
FAILED tests/unit/test_routing.py::test_route_after_understand_logs_message_type
FAILED tests/unit/test_routing.py::test_route_after_understand_warns_unknown_message_type
FAILED tests/unit/test_routing.py::test_route_after_validate_logs_conversation_state
```

**Razón**: Estos tests usan logging y `caplog` pero pueden estar mal configurados.

**Acción requerida**:
1. ✅ **PRIMERO**: Revisar y arreglar estos 4 tests
2. ✅ Documentar el fix en commit message
3. ✅ Luego proceder con tests nuevos

**Comando para verificar**:
```bash
uv run pytest tests/unit/test_routing.py -v
```

**Referencia**: `docs/analysis/REVISION_TAREAS_BACKLOG_TESTS.md` - Sección 1, Task 311

### Entregables

- [ ] Tests para route_after_understand (todos los MessageType)
- [ ] Tests para route_after_validate (valid/invalid, slots filled)
- [ ] Tests para route_after_correction/modification
- [ ] Tests para route_after_collect_next_slot
- [ ] Tests para route_after_action
- [ ] Tests para route_after_confirmation (yes/no/unclear)
- [ ] Tests para should_continue_flow
- [ ] Tests para activate_flow_by_intent
- [ ] Tests para create_branch_router
- [ ] Tests para edge cases especiales
- [ ] Cobertura >85% para el módulo

### Implementación Detallada

**Archivo(s) a crear/modificar:** `tests/unit/test_dm_routing.py`

#### Optimización: Tests Parametrizados

**En lugar de crear un test por cada MessageType, usar parametrización para reducir duplicación**:

```python
import pytest

@pytest.mark.parametrize("message_type,expected_node", [
    ("slot_value", "validate_slot"),
    ("correction", "handle_correction"),
    ("modification", "handle_modification"),
    ("confirmation", "handle_confirmation"),
    ("intent_change", "handle_intent_change"),
    ("question", "handle_digression"),
    ("help", "handle_digression"),
])
def test_route_after_understand_message_types(
    create_state_with_flow,
    message_type,
    expected_node
):
    """Test routing para todos los message types (parametrizado)."""
    # Arrange
    state = create_state_with_flow("book_flight")
    state["nlu_result"] = {
        "message_type": message_type,
        "command": "continue",
        "slots": []
    }

    # Act
    from soni.dm.routing import route_after_understand
    result = route_after_understand(state)

    # Assert
    assert result == expected_node
```

**Beneficio**: Reduce de ~8 tests individuales a 1 test parametrizado con 7 casos.

#### Ejemplo: Tests de Logging con caplog

**Para tests que verifican logging correctamente**:

```python
import logging

def test_route_after_understand_logs_message_type(caplog, create_state_with_flow):
    """Test que routing logea message_type correctamente."""
    # Arrange
    state = create_state_with_flow("book_flight")
    state["nlu_result"] = {
        "message_type": "slot_value",
        "command": "continue",
        "slots": []
    }

    # Act
    from soni.dm.routing import route_after_understand
    with caplog.at_level(logging.INFO):
        route_after_understand(state)

    # Assert
    assert "message_type=slot_value" in caplog.text
```

**Nota**: Usar `caplog.at_level(logging.INFO)` para capturar logs del nivel correcto.

### Tests Requeridos

**Archivo de tests:** `tests/unit/test_dm_routing.py`

**Tests específicos:**

- [ ] **route_after_understand** (~12 tests)
  - [ ] test_route_after_understand_intent_change
  - [ ] test_route_after_understand_slot_value
  - [ ] test_route_after_understand_slot_value_when_confirming
  - [ ] test_route_after_understand_slot_value_modification_after_denial
  - [ ] test_route_after_understand_digression
  - [ ] test_route_after_understand_confirmation
  - [ ] test_route_after_understand_correction
  - [ ] test_route_after_understand_modification
  - [ ] test_route_after_understand_cancellation
  - [ ] test_route_after_understand_no_nlu_result
  - [ ] test_route_after_understand_unknown_message_type
  - [ ] test_route_after_understand_no_active_flow

- [ ] **route_after_validate** (~8 tests)
  - [ ] test_route_after_validate_slot_valid
  - [ ] test_route_after_validate_slot_invalid
  - [ ] test_route_after_validate_all_slots_filled
  - [ ] test_route_after_validate_needs_confirmation
  - [ ] test_route_after_validate_ready_for_action
  - [ ] test_route_after_validate_correction_detected
  - [ ] test_route_after_validate_modification_detected
  - [ ] test_route_after_validate_error_state

- [ ] **route_after_correction** (~5 tests)
  - [ ] test_route_after_correction_back_to_collect
  - [ ] test_route_after_correction_back_to_confirmation
  - [ ] test_route_after_correction_back_to_action
  - [ ] test_route_after_correction_all_slots_filled
  - [ ] test_route_after_correction_error_state

- [ ] **route_after_modification** (~5 tests)
  - [ ] test_route_after_modification_back_to_collect
  - [ ] test_route_after_modification_back_to_confirmation
  - [ ] test_route_after_modification_back_to_action
  - [ ] test_route_after_modification_all_slots_filled
  - [ ] test_route_after_modification_error_state

- [ ] **route_after_collect_next_slot** (~5 tests)
  - [ ] test_route_after_collect_next_slot_has_next_slot
  - [ ] test_route_after_collect_next_slot_no_next_slot
  - [ ] test_route_after_collect_next_slot_ready_for_action
  - [ ] test_route_after_collect_next_slot_ready_for_confirmation
  - [ ] test_route_after_collect_next_slot_error_state

- [ ] **route_after_action** (~5 tests)
  - [ ] test_route_after_action_success
  - [ ] test_route_after_action_failure
  - [ ] test_route_after_action_has_next_step
  - [ ] test_route_after_action_flow_completed
  - [ ] test_route_after_action_error_state

- [ ] **route_after_confirmation** (~6 tests)
  - [ ] test_route_after_confirmation_yes
  - [ ] test_route_after_confirmation_no
  - [ ] test_route_after_confirmation_unclear
  - [ ] test_route_after_confirmation_correction_during
  - [ ] test_route_after_confirmation_modification_during
  - [ ] test_route_after_confirmation_error_state

- [ ] **should_continue_flow** (~3 tests)
  - [ ] test_should_continue_flow_has_next_step
  - [ ] test_should_continue_flow_no_next_step
  - [ ] test_should_continue_flow_at_end

- [ ] **activate_flow_by_intent** (~6 tests)
  - [ ] test_activate_flow_by_intent_exact_match
  - [ ] test_activate_flow_by_intent_normalized_match
  - [ ] test_activate_flow_by_intent_no_match
  - [ ] test_activate_flow_by_intent_already_active
  - [ ] test_activate_flow_by_intent_with_spaces
  - [ ] test_activate_flow_by_intent_with_hyphens

- [ ] **create_branch_router** (~5 tests)
  - [ ] test_create_branch_router_simple_case
  - [ ] test_create_branch_router_multiple_cases
  - [ ] test_create_branch_router_missing_variable
  - [ ] test_create_branch_router_unmatched_value
  - [ ] test_create_branch_router_nested_slots

**Total estimado**: ~60 tests

### Criterios de Éxito

- [ ] Todos los tests pasan (100% pass rate)
- [ ] Cobertura >85% para `dm/routing.py`
- [ ] Todos los MessageType están cubiertos
- [ ] Edge cases especiales están cubiertos
- [ ] Linting pasa sin errores
- [ ] Type checking pasa sin errores

### Validación Manual

```bash
uv run pytest tests/unit/test_dm_routing.py -v
uv run pytest tests/unit/test_dm_routing.py \
    --cov=src/soni/dm/routing \
    --cov-report=term-missing
```

### Referencias

- `docs/analysis/ANALISIS_TESTS_UNITARIOS_COBERTURA.md` - Sección 2.3
- `docs/analysis/GUIA_IMPLEMENTACION_TESTS_UNITARIOS.md` - Sección 2.5
- `src/soni/dm/routing.py` - Código fuente

### Notas Adicionales

- **CRÍTICO**: Este es el módulo más importante de routing
- Enfocarse en edge cases especiales (confirming state, modification after denial)
- Verificar todas las transiciones de estado posibles
- Usar mocks deterministas para todos los casos
