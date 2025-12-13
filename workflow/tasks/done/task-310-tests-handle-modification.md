## Task: 310 - Tests Unitarios para handle_modification.py

**ID de tarea:** 310
**Hito:** Tests Unitarios - Cobertura >85% (Fase CRÍTICA)
**Dependencias:** task-308-update-conftest-fixtures.md, task-309-tests-handle-correction.md
**Duración estimada:** 1-2 días

### Objetivo

Implementar tests unitarios exhaustivos para `dm/nodes/handle_modification.py` para alcanzar cobertura >85% (actualmente 6%). Estructura similar a handle_correction pero verificando flags de modification.

### Contexto

Según `docs/analysis/ANALISIS_TESTS_UNITARIOS_COBERTURA.md`:
- **Cobertura actual**: 6%
- **Gap**: 79%
- **LOC**: 264 líneas
- **Tests estimados**: ~25 tests
- **Prioridad**: CRÍTICA - Patrón conversacional fundamental

El módulo es muy similar a `handle_correction.py` pero:
- Setea flags de **modification** (no correction)
- Limpia flags de **correction** cuando setea modification
- Usa mensajes de acknowledgment específicos de modification

### Entregables

- [ ] Tests idénticos a handle_correction pero con modification flags
- [ ] Tests verificando que limpia correction flags
- [ ] Tests de routing post-modification
- [ ] Tests de estados previos
- [ ] Tests de metadata y response específicos de modification
- [ ] Cobertura >85% para el módulo
- [ ] Todos los tests pasan y son deterministas

### Implementación Detallada

**Archivo(s) a crear/modificar:** `tests/unit/test_dm_nodes_handle_modification.py`

**Estrategia**: Copiar estructura de tests de `handle_correction.py` pero:
1. Usar `mock_nlu_modification` en lugar de `mock_nlu_correction`
2. Verificar `_modification_slot` y `_modification_value` en metadata
3. Verificar que `_correction_slot` se limpia
4. Usar mensajes de acknowledgment de modification

#### Ejemplo: Test de Metadata Flags (Diferencia clave con correction)

```python
@pytest.mark.asyncio
async def test_handle_modification_no_flag_conflict_with_correction(
    create_state_with_slots,
    create_nlu_mock,
    mock_runtime
):
    """Test que modification flags no tienen conflicto con correction flags."""
    # Arrange
    state = create_state_with_slots("book_flight", slots={"destination": "Madrid"})
    # Estado previo tiene correction flags
    state["metadata"]["_correction_slot"] = "origin"
    state["metadata"]["_correction_value"] = "Barcelona"

    # Mock NLU result para modification
    state["nlu_result"] = {
        "message_type": "modification",
        "command": "continue",
        "slots": [{"name": "destination", "value": "Valencia"}],
        "confidence": 0.95
    }

    mock_runtime.context["normalizer"].normalize_slot.return_value = "Valencia"

    # Act
    result = await handle_modification_node(state, mock_runtime)

    # Assert - Modification flags seteados
    assert result["metadata"]["_modification_slot"] == "destination"
    assert result["metadata"]["_modification_value"] == "Valencia"

    # Assert - Correction flags limpiados
    assert "_correction_slot" not in result["metadata"]
    assert "_correction_value" not in result["metadata"]
```

**IMPORTANTE**: Los edge cases deben usar `assert result.get("conversation_state") == "error"` en lugar de `with pytest.raises()` porque el código retorna estados de error en lugar de lanzar excepciones.

```python
# ❌ INCORRECTO
@pytest.mark.asyncio
async def test_handle_modification_no_nlu_result(state, mock_runtime):
    state["nlu_result"] = None
    with pytest.raises((ValueError, KeyError)):
        await handle_modification_node(state, mock_runtime)

# ✅ CORRECTO
@pytest.mark.asyncio
async def test_handle_modification_no_nlu_result(state, mock_runtime):
    state["nlu_result"] = None
    result = await handle_modification_node(state, mock_runtime)
    assert result.get("conversation_state") == "error"
```

### Tests Requeridos

**Archivo de tests:** `tests/unit/test_dm_nodes_handle_modification.py`

**Tests específicos (similar a correction pero con modification):**

- [ ] **Formatos de slots**
  - [ ] test_handle_modification_slotvalue_format
  - [ ] test_handle_modification_dict_format
  - [ ] test_handle_modification_unknown_format

- [ ] **Edge cases**
  - [ ] test_handle_modification_no_nlu_result
  - [ ] test_handle_modification_no_slots
  - [ ] test_handle_modification_no_active_flow
  - [ ] test_handle_modification_normalization_failure

- [ ] **Routing post-modification**
  - [ ] test_handle_modification_returns_to_collect_step
  - [ ] test_handle_modification_returns_to_confirmation_step
  - [ ] test_handle_modification_returns_to_action_step
  - [ ] test_handle_modification_all_slots_filled_routes_to_confirmation

- [ ] **Estados previos**
  - [ ] test_handle_modification_from_ready_for_action
  - [ ] test_handle_modification_from_ready_for_confirmation
  - [ ] test_handle_modification_after_denial

- [ ] **Metadata y response (CRÍTICO - diferencia con correction)**
  - [ ] test_handle_modification_sets_modification_flags
  - [ ] test_handle_modification_clears_correction_flags
  - [ ] test_handle_modification_no_flag_conflict_with_correction
  - [ ] test_handle_modification_acknowledgment_message

- [ ] **_get_response_template**
  - [ ] test_get_response_template_modification_from_config
  - [ ] test_get_response_template_modification_default

**Total estimado**: ~25 tests

### Criterios de Éxito

- [ ] Todos los tests pasan (100% pass rate)
- [ ] Cobertura >85% para `dm/nodes/handle_modification.py`
- [ ] Tests verifican diferencia con correction (modification flags)
- [ ] Tests verifican que correction flags se limpian
- [ ] Linting pasa sin errores
- [ ] Type checking pasa sin errores

### Validación Manual

```bash
uv run pytest tests/unit/test_dm_nodes_handle_modification.py -v
uv run pytest tests/unit/test_dm_nodes_handle_modification.py \
    --cov=src/soni/dm/nodes/handle_modification \
    --cov-report=term-missing
```

### Referencias

- `docs/analysis/ANALISIS_TESTS_UNITARIOS_COBERTURA.md` - Sección 2.2
- `docs/analysis/GUIA_IMPLEMENTACION_TESTS_UNITARIOS.md` - Sección 2.2
- `task-309-tests-handle-correction.md` - Estructura similar

### Notas Adicionales

- **CRÍTICO**: Verificar que modification flags se setean y correction flags se limpian
- **IMPORTANTE**: Los edge cases deben verificar que el código retorna `{"conversation_state": "error"}` en lugar de usar `with pytest.raises()`, ya que el código no lanza excepciones sino que retorna estados de error
- **MetadataManager**: Considerar usar `MetadataManager` para manejo centralizado de flags. Si se implementa, adaptar tests para verificar que usa el manager correctamente
- Reutilizar estructura de tests de handle_correction pero adaptar assertions
- Enfocarse en diferencias con correction (flags de metadata)
- **Verificar que no hay conflicto entre flags**: Agregar test específico que verifica que cuando se setean flags de modification, los flags de correction se limpian completamente y viceversa
