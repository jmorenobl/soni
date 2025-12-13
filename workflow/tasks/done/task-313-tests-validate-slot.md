## Task: 313 - Tests Unitarios para validate_slot.py

**ID de tarea:** 313
**Hito:** Tests Unitarios - Cobertura >85% (Fase CRÍTICA)
**Dependencias:** task-308-update-conftest-fixtures.md (requiere fixtures de validators)
**Duración estimada:** 2-3 días

### Objetivo

Implementar tests unitarios exhaustivos para `dm/nodes/validate_slot.py` para alcanzar cobertura >85% (actualmente 46%).

### Contexto

Según `docs/analysis/ANALISIS_TESTS_UNITARIOS_COBERTURA.md`:
- **Cobertura actual**: 46%
- **Gap**: 39%
- **LOC**: 190 líneas
- **Tests estimados**: ~30-40 tests
- **Prioridad**: CRÍTICA - Validación es crítica para calidad de datos

El módulo maneja:
- Validación de slots con validators registrados
- Normalización de valores
- Slot filling logic
- Manejo de errores de validación

### Entregables

- [ ] Tests para validación exitosa
- [ ] Tests para validación fallida
- [ ] Tests para normalización
- [ ] Tests para edge cases (sin validator, validator retorna None, excepciones)
- [ ] Tests para slot filling logic
- [ ] Cobertura >85% para el módulo

### Tests Requeridos

**Archivo de tests:** `tests/unit/test_dm_nodes_validate_slot.py`

**Tests específicos:**

- [ ] **Validación exitosa** (~5 tests)
  - [ ] test_validate_slot_valid_advances
  - [ ] test_validate_slot_all_slots_filled_confirmation
  - [ ] test_validate_slot_all_slots_filled_action
  - [ ] test_validate_slot_sets_slot_value
  - [ ] test_validate_slot_updates_conversation_state

- [ ] **Validación fallida** (~5 tests)
  - [ ] test_validate_slot_invalid_recollects
  - [ ] test_validate_slot_invalid_error_message
  - [ ] test_validate_slot_invalid_no_advance
  - [ ] test_validate_slot_invalid_preserves_state
  - [ ] test_validate_slot_invalid_metadata

- [ ] **Normalización** (~4 tests)
  - [ ] test_validate_slot_normalization_success
  - [ ] test_validate_slot_normalization_failure
  - [ ] test_validate_slot_normalization_preserves_original
  - [ ] test_validate_slot_normalization_updates_value

- [ ] **Edge cases** (~8 tests)
  - [ ] test_validate_slot_no_validator_defined
  - [ ] test_validate_slot_validator_returns_none
  - [ ] test_validate_slot_validator_raises_exception
  - [ ] test_validate_slot_no_nlu_result
  - [ ] test_validate_slot_no_active_flow
  - [ ] test_validate_slot_no_slot_in_nlu
  - [ ] test_validate_slot_multiple_slots_in_nlu
  - [ ] test_validate_slot_empty_value

- [ ] **Slot filling logic** (~8 tests)
  - [ ] test_validate_slot_fills_single_slot
  - [ ] test_validate_slot_fills_multiple_slots
  - [ ] test_validate_slot_updates_existing_slot
  - [ ] test_validate_slot_preserves_other_slots
  - [ ] test_validate_slot_uses_flow_id
  - [ ] test_validate_slot_handles_slotvalue_format
  - [ ] test_validate_slot_handles_dict_format
  - [ ] test_validate_slot_handles_mixed_format

**Total estimado**: ~30 tests

### Criterios de Éxito

- [ ] Todos los tests pasan (100% pass rate)
- [ ] Cobertura >85% para `dm/nodes/validate_slot.py`
- [ ] Tests cubren todos los casos de validación
- [ ] Tests cubren normalización exitosa y fallida
- [ ] Tests cubren edge cases
- [ ] Linting pasa sin errores
- [ ] Type checking pasa sin errores

### Validación Manual

```bash
uv run pytest tests/unit/test_dm_nodes_validate_slot.py -v
uv run pytest tests/unit/test_dm_nodes_validate_slot.py \
    --cov=src/soni/dm/nodes/validate_slot \
    --cov-report=term-missing
```

### Referencias

- `docs/analysis/ANALISIS_TESTS_UNITARIOS_COBERTURA.md` - Sección 2.4.5
- `docs/analysis/GUIA_IMPLEMENTACION_TESTS_UNITARIOS.md` - Sección 3.4
- `src/soni/dm/nodes/validate_slot.py` - Código fuente

### Notas Adicionales

- **IMPORTANTE**: Esta tarea requiere validator fixtures en task-308. Asegurar que task-308 incluye fixtures como `mock_validator_success`, `mock_validator_failure`, y `mock_validator_registry`
- Mockear validators registrados para tests deterministas
- Verificar que normalización se ejecuta antes de validación
- Enfocarse en slot filling logic y preservación de otros slots
- **Validator Fixtures Requeridos** (deben estar en conftest.py):
  ```python
  @pytest.fixture
  def mock_validator_success():
      """Mock validator que siempre retorna True (valid)."""
      validator = MagicMock()
      validator.validate.return_value = True
      return validator

  @pytest.fixture
  def mock_validator_failure():
      """Mock validator que siempre retorna False (invalid)."""
      validator = MagicMock()
      validator.validate.return_value = False
      return validator

  @pytest.fixture
  def mock_validator_registry():
      """Mock registry de validators."""
      registry = MagicMock()
      return registry
  ```
- **Ejemplo de uso en tests**:
  ```python
  @pytest.mark.asyncio
  async def test_validate_slot_valid_advances(
      create_state_with_slots,
      mock_runtime,
      mock_validator_success
  ):
      """Test que validación exitosa avanza al siguiente step."""
      # Arrange
      state = create_state_with_slots("book_flight", slots={})
      state["nlu_result"] = {"slots": [{"name": "origin", "value": "Madrid"}]}

      # Mock validator registry
      mock_runtime.context["validator_registry"].get_validator.return_value = mock_validator_success

      # Act
      result = await validate_slot_node(state, mock_runtime)

      # Assert
      assert mock_validator_success.validate.called
      assert result["flow_slots"]["flow_1"]["origin"] == "Madrid"
  ```
