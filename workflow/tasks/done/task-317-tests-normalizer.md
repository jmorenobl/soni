## Task: 317 - Tests Unitarios para du/normalizer.py

**ID de tarea:** 317
**Hito:** Tests Unitarios - Cobertura >85% (Fase ALTA)
**Dependencias:** task-308-update-conftest-fixtures.md
**Duración estimada:** 1 día

### Objetivo

Implementar tests unitarios para `du/normalizer.py` para alcanzar cobertura >85% (actualmente 67%).

### Contexto

Según `docs/analysis/ANALISIS_TESTS_UNITARIOS_COBERTURA.md`:
- **Cobertura actual**: 67%
- **Gap**: 18%
- **LOC**: 132 líneas
- **Tests estimados**: ~10-15 tests
- **Prioridad**: ALTA

El módulo normaliza valores de slots usando LLM. Tests deben usar mocks de LLM.

### Entregables

- [ ] Tests para normalize_slot con mock LLM
- [ ] Tests para diferentes tipos de slots
- [ ] Tests para edge cases
- [ ] Tests para error handling
- [ ] Cobertura >85% para el módulo

### Tests Requeridos

**Archivo de tests:** `tests/unit/test_du_normalizer.py`

**Tests específicos:**

- [ ] **normalize_slot** (~8 tests)
  - [ ] test_normalize_slot_success
  - [ ] test_normalize_slot_with_mock_lm
  - [ ] test_normalize_slot_date_type
  - [ ] test_normalize_slot_city_type
  - [ ] test_normalize_slot_number_type
  - [ ] test_normalize_slot_string_type
  - [ ] test_normalize_slot_preserves_value_if_no_normalizer
  - [ ] test_normalize_slot_handles_none_value

- [ ] **Error handling** (~4 tests)
  - [ ] test_normalize_slot_llm_error
  - [ ] test_normalize_slot_timeout
  - [ ] test_normalize_slot_invalid_response
  - [ ] test_normalize_slot_fallback_to_original

- [ ] **Edge cases** (~3 tests)
  - [ ] test_normalize_slot_empty_string
  - [ ] test_normalize_slot_whitespace_only
  - [ ] test_normalize_slot_special_characters

**Total estimado**: ~15 tests

### Criterios de Éxito

- [ ] Todos los tests pasan (100% pass rate)
- [ ] Cobertura >85% para `du/normalizer.py`
- [ ] Todos los tests usan mocks de LLM (nunca LLM real)
- [ ] Linting pasa sin errores
- [ ] Type checking pasa sin errores

### Validación Manual

```bash
uv run pytest tests/unit/test_du_normalizer.py -v
uv run pytest tests/unit/test_du_normalizer.py \
    --cov=src/soni/du/normalizer \
    --cov-report=term-missing
```

### Referencias

- `docs/analysis/ANALISIS_TESTS_UNITARIOS_COBERTURA.md` - Sección 2.5 (Prioridad ALTA)
- `src/soni/du/normalizer.py` - Código fuente

### Notas Adicionales

- **CRÍTICO**: Usar mocks de LLM para determinismo
- No usar LLM real en tests unitarios
- Enfocarse en lógica de normalización, no en resultados de LLM
