## Task: 315 - Tests Unitarios para runtime/runtime.py

**ID de tarea:** 315
**Hito:** Tests Unitarios - Cobertura >85% (Fase ALTA)
**Dependencias:** task-308-update-conftest-fixtures.md
**Duración estimada:** 1-2 días

### Objetivo

Implementar tests unitarios para `runtime/runtime.py` para alcanzar cobertura >85% (actualmente 59%).

### Contexto

Según `docs/analysis/ANALISIS_TESTS_UNITARIOS_COBERTURA.md`:
- **Cobertura actual**: 59%
- **Gap**: 26%
- **LOC**: 250 líneas
- **Tests estimados**: ~20-30 tests
- **Prioridad**: ALTA - Orquestación principal

El módulo RuntimeLoop orquesta el procesamiento de mensajes.

### Entregables

- [ ] Tests para process_message
- [ ] Tests para manejo de estado (checkpoint, resume)
- [ ] Tests para delegación a componentes
- [ ] Tests para edge cases
- [ ] Cobertura >85% para el módulo

### Tests Requeridos

**Archivo de tests:** `tests/unit/test_runtime_runtime.py`

**Tests específicos:**

- [ ] **process_message** (~10 tests)
  - [ ] test_process_message_first_turn
  - [ ] test_process_message_resume_flow
  - [ ] test_process_message_new_flow
  - [ ] test_process_message_delegates_to_graph
  - [ ] test_process_message_returns_response
  - [ ] test_process_message_handles_errors
  - [ ] test_process_message_checkpoints_state
  - [ ] test_process_message_updates_state
  - [ ] test_process_message_empty_message
  - [ ] test_process_message_none_message

- [ ] **Estado y checkpointing** (~8 tests)
  - [ ] test_runtime_saves_checkpoint
  - [ ] test_runtime_loads_checkpoint
  - [ ] test_runtime_resumes_from_checkpoint
  - [ ] test_runtime_no_checkpoint_creates_new
  - [ ] test_runtime_checkpoint_error_handling
  - [ ] test_runtime_state_serialization
  - [ ] test_runtime_state_deserialization
  - [ ] test_runtime_state_validation

- [ ] **Delegación** (~6 tests)
  - [ ] test_runtime_delegates_to_flow_manager
  - [ ] test_runtime_delegates_to_nlu
  - [ ] test_runtime_delegates_to_action_handler
  - [ ] test_runtime_delegates_to_digression_handler
  - [ ] test_runtime_delegates_to_graph
  - [ ] test_runtime_context_injection

- [ ] **Edge cases** (~6 tests)
  - [ ] test_runtime_no_config
  - [ ] test_runtime_no_graph
  - [ ] test_runtime_invalid_user_id
  - [ ] test_runtime_concurrent_requests
  - [ ] test_runtime_timeout_handling
  - [ ] test_runtime_error_recovery

**Total estimado**: ~30 tests

### Criterios de Éxito

- [ ] Todos los tests pasan (100% pass rate)
- [ ] Cobertura >85% para `runtime/runtime.py`
- [ ] Tests mockean todas las dependencias
- [ ] Linting pasa sin errores
- [ ] Type checking pasa sin errores

### Validación Manual

```bash
uv run pytest tests/unit/test_runtime_runtime.py -v
uv run pytest tests/unit/test_runtime_runtime.py \
    --cov=src/soni/runtime/runtime \
    --cov-report=term-missing
```

### Referencias

- `docs/analysis/ANALISIS_TESTS_UNITARIOS_COBERTURA.md` - Sección 2.5 (Prioridad ALTA)
- `src/soni/runtime/runtime.py` - Código fuente

### Notas Adicionales

- Mockear todas las dependencias (graph, flow_manager, nlu, etc.)
- Enfocarse en orquestación, no en lógica de negocio
- Verificar que delegación funciona correctamente
