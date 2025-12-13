## Task: 319 - Tests Unitarios Adicionales para handle_intent_change.py

**ID de tarea:** 319
**Hito:** Tests Unitarios - Cobertura >85% (Fase ALTA)
**Dependencias:** task-308-update-conftest-fixtures.md
**Duración estimada:** 1 día

### Objetivo

Implementar tests unitarios adicionales para `dm/nodes/handle_intent_change.py` para alcanzar cobertura >85% (actualmente 69%).

### Contexto

Según `docs/analysis/ANALISIS_TESTS_UNITARIOS_COBERTURA.md`:
- **Cobertura actual**: 69%
- **Gap**: 16%
- **LOC**: 210 líneas
- **Tests estimados**: ~10-15 tests adicionales
- **Prioridad**: ALTA

El módulo ya tiene algunos tests, pero faltan casos específicos.

### Entregables

- [ ] Tests para _extract_slots_from_nlu
- [ ] Tests para casos adicionales de handle_intent_change_node
- [ ] Tests para edge cases
- [ ] Cobertura >85% para el módulo

### Tests Requeridos

**Archivo de tests:** `tests/unit/test_dm_nodes_handle_intent_change.py` (agregar tests)

**Tests específicos:**

- [ ] **_extract_slots_from_nlu** (~7 tests)
  - [ ] test_extract_slots_from_nlu_dict_format
  - [ ] test_extract_slots_from_nlu_slotvalue_format
  - [ ] test_extract_slots_from_nlu_mixed_format
  - [ ] test_extract_slots_from_nlu_empty_list
  - [ ] test_extract_slots_from_nlu_missing_name
  - [ ] test_extract_slots_from_nlu_missing_value
  - [ ] test_extract_slots_from_nlu_none_value

- [ ] **handle_intent_change_node casos adicionales** (~8 tests)
  - [ ] test_handle_intent_change_extracts_multiple_slots
  - [ ] test_handle_intent_change_preserves_existing_slots
  - [ ] test_handle_intent_change_flow_already_active
  - [ ] test_handle_intent_change_no_nlu_result
  - [ ] test_handle_intent_change_command_not_flow_but_active_flow
  - [ ] test_handle_intent_change_advances_through_completed_steps
  - [ ] test_handle_intent_change_clears_user_message
  - [ ] test_handle_intent_change_updates_conversation_state

**Total estimado**: ~15 tests

### Criterios de Éxito

- [ ] Todos los tests pasan (100% pass rate)
- [ ] Cobertura >85% para `dm/nodes/handle_intent_change.py`
- [ ] Linting pasa sin errores
- [ ] Type checking pasa sin errores

### Validación Manual

```bash
uv run pytest tests/unit/test_dm_nodes_handle_intent_change.py -v
uv run pytest tests/unit/test_dm_nodes_handle_intent_change.py \
    --cov=src/soni/dm/nodes/handle_intent_change \
    --cov-report=term-missing
```

### Referencias

- `docs/analysis/ANALISIS_TESTS_UNITARIOS_COBERTURA.md` - Sección 2.4.1
- `src/soni/dm/nodes/handle_intent_change.py` - Código fuente
