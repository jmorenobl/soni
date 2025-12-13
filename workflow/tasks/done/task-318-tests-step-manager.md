## Task: 318 - Tests Unitarios para flow/step_manager.py

**ID de tarea:** 318
**Hito:** Tests Unitarios - Cobertura >85% (Fase ALTA)
**Dependencias:** task-308-update-conftest-fixtures.md
**Duración estimada:** 1 día

### Objetivo

Implementar tests unitarios para `flow/step_manager.py` para alcanzar cobertura >85% (actualmente 69%).

### Contexto

Según `docs/analysis/ANALISIS_TESTS_UNITARIOS_COBERTURA.md`:
- **Cobertura actual**: 69%
- **Gap**: 16%
- **LOC**: 168 líneas
- **Tests estimados**: ~15-20 tests
- **Prioridad**: ALTA

El módulo gestiona avance de steps en flows.

### Entregables

- [ ] Tests para advance_to_next_step
- [ ] Tests para get_current_step_config
- [ ] Tests para get_next_step_config
- [ ] Tests para edge cases
- [ ] Cobertura >85% para el módulo

### Tests Requeridos

**Archivo de tests:** `tests/unit/test_flow_step_manager.py`

**Tests específicos:**

- [ ] **advance_to_next_step** (~6 tests)
  - [ ] test_advance_to_next_step_success
  - [ ] test_advance_to_next_step_updates_current_step
  - [ ] test_advance_to_next_step_no_next_step
  - [ ] test_advance_to_next_step_at_end
  - [ ] test_advance_to_next_step_preserves_other_state
  - [ ] test_advance_to_next_step_updates_conversation_state

- [ ] **get_current_step_config** (~4 tests)
  - [ ] test_get_current_step_config_exists
  - [ ] test_get_current_step_config_not_exists
  - [ ] test_get_current_step_config_no_active_flow
  - [ ] test_get_current_step_config_returns_config

- [ ] **get_next_step_config** (~4 tests)
  - [ ] test_get_next_step_config_exists
  - [ ] test_get_next_step_config_not_exists
  - [ ] test_get_next_step_config_at_end
  - [ ] test_get_next_step_config_returns_config

- [ ] **Edge cases** (~6 tests)
  - [ ] test_step_manager_no_flow_stack
  - [ ] test_step_manager_empty_flow_stack
  - [ ] test_step_manager_invalid_step
  - [ ] test_step_manager_step_out_of_bounds
  - [ ] test_step_manager_preserves_flow_id
  - [ ] test_step_manager_preserves_flow_name

**Total estimado**: ~20 tests

### Criterios de Éxito

- [ ] Todos los tests pasan (100% pass rate)
- [ ] Cobertura >85% para `flow/step_manager.py`
- [ ] Linting pasa sin errores
- [ ] Type checking pasa sin errores

### Validación Manual

```bash
uv run pytest tests/unit/test_flow_step_manager.py -v
uv run pytest tests/unit/test_flow_step_manager.py \
    --cov=src/soni/flow/step_manager \
    --cov-report=term-missing
```

### Referencias

- `docs/analysis/ANALISIS_TESTS_UNITARIOS_COBERTURA.md` - Sección 2.5 (Prioridad ALTA)
- `src/soni/flow/step_manager.py` - Código fuente
