## Task: 316 - Tests Unitarios para utils/response_generator.py

**ID de tarea:** 316
**Hito:** Tests Unitarios - Cobertura >85% (Fase ALTA)
**Dependencias:** task-308-update-conftest-fixtures.md
**Duración estimada:** 4-6 horas

### Objetivo

Implementar tests unitarios para `utils/response_generator.py` para alcanzar cobertura >85% (actualmente 61%).

### Contexto

Según `docs/analysis/ANALISIS_TESTS_UNITARIOS_COBERTURA.md`:
- **Cobertura actual**: 61%
- **Gap**: 24%
- **LOC**: 41 líneas
- **Tests estimados**: ~5-8 tests
- **Prioridad**: ALTA

El módulo genera respuestas del sistema (confirmación, error, help).

### Entregables

- [ ] Tests para generate_confirmation
- [ ] Tests para generate_error_message
- [ ] Tests para generate_help_message
- [ ] Tests para interpolate_slots
- [ ] Cobertura >85% para el módulo

### Tests Requeridos

**Archivo de tests:** `tests/unit/test_utils_response_generator.py`

**Tests específicos:**

- [ ] **generate_confirmation** (~3 tests)
  - [ ] test_response_generator_generate_confirmation
  - [ ] test_response_generator_generate_confirmation_with_template
  - [ ] test_response_generator_generate_confirmation_no_template

- [ ] **generate_error_message** (~2 tests)
  - [ ] test_response_generator_generate_error_message
  - [ ] test_response_generator_generate_error_message_with_context

- [ ] **generate_help_message** (~1 test)
  - [ ] test_response_generator_generate_help_message

- [ ] **interpolate_slots** (~2 tests)
  - [ ] test_response_generator_interpolate_slots
  - [ ] test_response_generator_interpolate_slots_missing_slot

**Total estimado**: ~8 tests

### Criterios de Éxito

- [ ] Todos los tests pasan (100% pass rate)
- [ ] Cobertura >85% para `utils/response_generator.py`
- [ ] Linting pasa sin errores
- [ ] Type checking pasa sin errores

### Validación Manual

```bash
uv run pytest tests/unit/test_utils_response_generator.py -v
uv run pytest tests/unit/test_utils_response_generator.py \
    --cov=src/soni/utils/response_generator \
    --cov-report=term-missing
```

### Referencias

- `docs/analysis/ANALISIS_TESTS_UNITARIOS_COBERTURA.md` - Sección 2.6.4
- `src/soni/utils/response_generator.py` - Código fuente
