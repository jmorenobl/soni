## Task: 322 - Tests Unitarios Adicionales para utils/flow_cleanup.py

**ID de tarea:** 322
**Hito:** Tests Unitarios - Cobertura >85% (Fase FINAL)
**Dependencias:** task-308-update-conftest-fixtures.md
**Duración estimada:** 2-3 horas

### Objetivo

Implementar tests unitarios adicionales para `utils/flow_cleanup.py` para alcanzar cobertura >96% (actualmente 96%).

### Contexto

Según `docs/analysis/ANALISIS_TESTS_UNITARIOS_COBERTURA.md`:
- **Cobertura actual**: 96%
- **Gap**: ~1-2 edge cases
- **LOC**: ~100 líneas
- **Tests estimados**: ~1-2 tests adicionales
- **Prioridad**: FINAL - Ya tiene excelente cobertura

El módulo ya tiene excelente cobertura, solo revisar edge cases.

### Entregables

- [ ] Tests para edge cases faltantes
- [ ] Cobertura >96% para el módulo

### Tests Requeridos

**Archivo de tests:** `tests/unit/test_utils_flow_cleanup.py` (agregar tests)

**Tests específicos:**

- [ ] **Edge cases** (~2 tests)
  - [ ] test_flow_cleanup_manager_edge_case_empty_stack
  - [ ] test_flow_cleanup_manager_edge_case_all_flows_active

**Total estimado**: ~2 tests

### Criterios de Éxito

- [ ] Todos los tests pasan (100% pass rate)
- [ ] Cobertura >96% para `utils/flow_cleanup.py`
- [ ] Linting pasa sin errores
- [ ] Type checking pasa sin errores

### Validación Manual

```bash
uv run pytest tests/unit/test_utils_flow_cleanup.py -v
uv run pytest tests/unit/test_utils_flow_cleanup.py \
    --cov=src/soni/utils/flow_cleanup \
    --cov-report=term-missing
```

### Referencias

- `docs/analysis/ANALISIS_TESTS_UNITARIOS_COBERTURA.md` - Sección 2.6.2
- `src/soni/utils/flow_cleanup.py` - Código fuente
