## Task: 312 - Tests Unitarios para handle_confirmation.py

**ID de tarea:** 312
**Hito:** Tests Unitarios - Cobertura >85% (Fase CRÍTICA)
**Dependencias:** task-308-update-conftest-fixtures.md, task-309-tests-handle-correction.md
**Duración estimada:** 1-2 días

### Objetivo

Implementar tests unitarios exhaustivos para `dm/nodes/handle_confirmation.py` para alcanzar cobertura >85% (actualmente 40%). Incluir tests para corrección durante confirmación.

### Contexto

Según `docs/analysis/ANALISIS_TESTS_UNITARIOS_COBERTURA.md`:
- **Cobertura actual**: 40%
- **Gap**: 45%
- **LOC**: 330 líneas
- **Tests estimados**: ~20-25 tests
- **Prioridad**: CRÍTICA - Confirmación es patrón conversacional crítico

El módulo maneja:
- Confirmación positiva (YES) → procede a acción
- Confirmación negativa (NO) → permite modificación
- Respuesta unclear → incrementa intentos, re-pregunta
- Max retries → error state
- Corrección durante confirmación → actualiza slot y re-genera confirmación

### Tests Existentes a Revisar

Ya existen algunos tests en `tests/unit/test_handle_confirmation_node.py`:

- ✅ `test_handle_confirmation_confirmed` - Revisar y completar
- ✅ `test_handle_confirmation_denied` - Revisar y completar
- ✅ `test_handle_confirmation_unclear_first_attempt` - Revisar y completar
- ✅ `test_handle_confirmation_max_retries_exceeded` - Revisar y completar

**Acción requerida**:
1. ✅ **PRIMERO**: Revisar tests existentes antes de crear nuevos
2. ✅ Completar tests existentes si faltan assertions o coverage
3. ✅ Agregar solo tests faltantes según checklist
4. ✅ Verificar que tests existentes siguen patrón AAA y usan fixtures correctos

**Comando para verificar tests existentes**:
```bash
uv run pytest tests/unit/test_handle_confirmation_node.py -v
```

### Entregables

- [ ] Tests para confirmación positiva (YES)
- [ ] Tests para confirmación negativa (NO)
- [ ] Tests para respuesta unclear
- [ ] Tests para max retries
- [ ] Tests para corrección durante confirmación
- [ ] Tests para _handle_correction_during_confirmation
- [ ] Tests para _get_response_template
- [ ] Cobertura >85% para el módulo

### Tests Requeridos

**Archivo de tests:** `tests/unit/test_dm_nodes_handle_confirmation.py`

**Tests específicos:**

- [ ] **Confirmación positiva** (~3 tests)
  - [ ] test_handle_confirmation_yes_proceeds_to_action
  - [ ] test_handle_confirmation_clears_flags_on_success
  - [ ] test_handle_confirmation_yes_metadata_cleanup

- [ ] **Confirmación negativa** (~3 tests)
  - [ ] test_handle_confirmation_no_allows_modification
  - [ ] test_handle_confirmation_no_clears_flags
  - [ ] test_handle_confirmation_no_message

- [ ] **Respuesta unclear** (~4 tests)
  - [ ] test_handle_confirmation_unclear_asks_again
  - [ ] test_handle_confirmation_unclear_increments_attempts
  - [ ] test_handle_confirmation_unclear_before_max_attempts
  - [ ] test_handle_confirmation_unclear_message

- [ ] **Max retries** (~3 tests)
  - [ ] test_handle_confirmation_max_attempts_exceeded
  - [ ] test_handle_confirmation_max_attempts_before_processing
  - [ ] test_handle_confirmation_max_attempts_clears_metadata

- [ ] **Corrección durante confirmación** (~6 tests)
  - [ ] test_handle_confirmation_correction_during_confirmation
  - [ ] test_handle_correction_during_confirmation_slotvalue_format
  - [ ] test_handle_correction_during_confirmation_dict_format
  - [ ] test_handle_correction_during_confirmation_no_slots
  - [ ] test_handle_correction_during_confirmation_updates_slot
  - [ ] test_handle_correction_during_confirmation_regenerates_confirmation
  - [ ] test_handle_correction_during_confirmation_combined_response

- [ ] **Edge cases** (~3 tests)
  - [ ] test_handle_confirmation_unexpected_message_type
  - [ ] test_handle_confirmation_no_nlu_result
  - [ ] test_handle_confirmation_clears_flags_on_error

- [ ] **_get_response_template** (~3 tests)
  - [ ] test_get_response_template_from_config
  - [ ] test_get_response_template_default
  - [ ] test_get_response_template_interpolation

**Total estimado**: ~25 tests

### Criterios de Éxito

- [ ] Todos los tests pasan (100% pass rate)
- [ ] Cobertura >85% para `dm/nodes/handle_confirmation.py`
- [ ] Tests cubren todos los casos de confirmación (yes/no/unclear)
- [ ] Tests cubren corrección durante confirmación
- [ ] Tests verifican max retries correctamente
- [ ] Linting pasa sin errores
- [ ] Type checking pasa sin errores

### Validación Manual

```bash
uv run pytest tests/unit/test_dm_nodes_handle_confirmation.py -v
uv run pytest tests/unit/test_dm_nodes_handle_confirmation.py \
    --cov=src/soni/dm/nodes/handle_confirmation \
    --cov-report=term-missing
```

### Referencias

- `docs/analysis/ANALISIS_TESTS_UNITARIOS_COBERTURA.md` - Sección 2.4.4
- `docs/analysis/GUIA_IMPLEMENTACION_TESTS_UNITARIOS.md` - Sección 2.3 y 2.4
- `src/soni/dm/nodes/handle_confirmation.py` - Código fuente

### Notas Adicionales

- **CRÍTICO**: Verificar que corrección durante confirmación re-genera mensaje de confirmación
- Enfocarse en lógica de max retries y cleanup de metadata
- Usar fixtures mock_nlu_confirmation_yes/no/unclear
