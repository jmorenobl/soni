## Task: 320 - Tests Unitarios Adicionales para flow/manager.py

**ID de tarea:** 320
**Hito:** Tests Unitarios - Cobertura >85% (Fase FINAL)
**Dependencias:** task-308-update-conftest-fixtures.md
**Duración estimada:** 4-6 horas

### Objetivo

Implementar tests unitarios adicionales para `flow/manager.py` para alcanzar cobertura >90% (actualmente 89%).

### Contexto

Según `docs/analysis/ANALISIS_TESTS_UNITARIOS_COBERTURA.md`:
- **Cobertura actual**: 89%
- **Gap**: ~5% para >90%
- **LOC**: ~300 líneas
- **Tests estimados**: ~5 tests adicionales
- **Prioridad**: FINAL - Ya tiene buena cobertura

El módulo ya tiene buena cobertura, solo faltan algunos edge cases.

### Entregables

- [ ] Tests para edge cases faltantes
- [ ] Tests para casos límite de stack
- [ ] Cobertura >90% para el módulo

### Tests Requeridos

**Archivo de tests:** `tests/unit/test_flow_manager.py` (agregar tests)

**Tests específicos:**

- [ ] **Edge cases** (~5 tests)
  - [ ] test_flow_manager_stack_limit_enforcement
  - [ ] test_flow_manager_stack_limit_strategy_cancel_oldest
  - [ ] test_flow_manager_stack_limit_strategy_reject_new
  - [ ] test_flow_manager_get_slot_nonexistent_flow_id
  - [ ] test_flow_manager_set_slot_nonexistent_flow_id

**Total estimado**: ~5 tests

### Criterios de Éxito

- [ ] Todos los tests pasan (100% pass rate)
- [ ] Cobertura >90% para `flow/manager.py`
- [ ] Linting pasa sin errores
- [ ] Type checking pasa sin errores

### Validación Manual

```bash
uv run pytest tests/unit/test_flow_manager.py -v
uv run pytest tests/unit/test_flow_manager.py \
    --cov=src/soni/flow/manager \
    --cov-report=term-missing
```

### Referencias

- `docs/analysis/ANALISIS_TESTS_UNITARIOS_COBERTURA.md` - Sección 2.5 (Módulos >80%)
- `src/soni/flow/manager.py` - Código fuente
