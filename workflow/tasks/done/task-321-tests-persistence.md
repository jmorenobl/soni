## Task: 321 - Tests Unitarios Adicionales para dm/persistence.py

**ID de tarea:** 321
**Hito:** Tests Unitarios - Cobertura >85% (Fase FINAL)
**Dependencias:** task-308-update-conftest-fixtures.md
**Duración estimada:** 4-6 horas

### Objetivo

Implementar tests unitarios adicionales para `dm/persistence.py` para alcanzar cobertura >85% (actualmente 84%).

### Contexto

Según `docs/analysis/ANALISIS_TESTS_UNITARIOS_COBERTURA.md`:
- **Cobertura actual**: 84%
- **Gap**: ~5% para >85%
- **LOC**: ~150 líneas
- **Tests estimados**: ~5 tests adicionales
- **Prioridad**: FINAL - Ya tiene buena cobertura

El módulo maneja creación de checkpointers. Faltan tests para CheckpointerFactory.

### Entregables

- [ ] Tests para CheckpointerFactory.create
- [ ] Tests para _create_sqlite_checkpointer
- [ ] Tests para _create_memory_checkpointer
- [ ] Tests para _create_none_checkpointer
- [ ] Tests para error handling
- [ ] Cobertura >85% para el módulo

### Tests Requeridos

**Archivo de tests:** `tests/unit/test_dm_persistence.py` (agregar tests)

**Tests específicos:**

- [ ] **CheckpointerFactory.create** (~6 tests)
  - [ ] test_checkpointer_factory_create_sqlite
  - [ ] test_checkpointer_factory_create_sqlite_connection_error
  - [ ] test_checkpointer_factory_create_sqlite_import_error
  - [ ] test_checkpointer_factory_create_memory
  - [ ] test_checkpointer_factory_create_none
  - [ ] test_checkpointer_factory_create_unsupported_backend

- [ ] **_create_sqlite_checkpointer** (~5 tests)
  - [ ] test_create_sqlite_checkpointer_success
  - [ ] test_create_sqlite_checkpointer_os_error
  - [ ] test_create_sqlite_checkpointer_connection_error
  - [ ] test_create_sqlite_checkpointer_import_error
  - [ ] test_create_sqlite_checkpointer_unexpected_error

- [ ] **_create_memory_checkpointer** (~2 tests)
  - [ ] test_create_memory_checkpointer_success
  - [ ] test_create_memory_checkpointer_returns_none_context

- [ ] **_create_none_checkpointer** (~1 test)
  - [ ] test_create_none_checkpointer_returns_none

**Total estimado**: ~14 tests

### Criterios de Éxito

- [ ] Todos los tests pasan (100% pass rate)
- [ ] Cobertura >85% para `dm/persistence.py`
- [ ] Linting pasa sin errores
- [ ] Type checking pasa sin errores

### Validación Manual

```bash
uv run pytest tests/unit/test_dm_persistence.py -v
uv run pytest tests/unit/test_dm_persistence.py \
    --cov=src/soni/dm/persistence \
    --cov-report=term-missing
```

### Referencias

- `docs/analysis/ANALISIS_TESTS_UNITARIOS_COBERTURA.md` - Sección 2.2
- `src/soni/dm/persistence.py` - Código fuente

### Notas Adicionales

- Mockear imports de langgraph.checkpoint para tests deterministas
- Enfocarse en error handling de creación de checkpointers
