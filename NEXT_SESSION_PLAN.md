# Plan para Completar los 42 Tests Restantes

## Estado Actual: 515/557 (92.5%) ✅

### Resumen de Progreso

**Completado:**
- ✅ Core schema migration (100%)
- ✅ All source code migrated (100%)
- ✅ 515 tests passing (92.5%)
- ✅ mypy: 0 errors
- ✅ ruff: 0 errors
- ✅ No `# type: ignore` comments

**Pendiente:**
- ⚠️ 42 tests need manual fixes (7.5%)

## Tests Restantes por Categoría

### Grupo 1: dm_graph (4 tests) - 10 min
**Archivos**: `tests/unit/test_dm_graph.py`

**Tests:**
1. `test_understand_node_with_message` - Remove pending_action assertion
2. `test_action_node_executes_handler` - Fix slot assertions
3. `test_collect_slot_node_already_filled` - Fix state creation
4. `test_action_node_missing_input_slot` - Fix error assertions

**Patrón común**:
- Eliminar `assert result["pending_action"]` (campo no existe en schema)
- Reemplazar `result["slots"]["key"]` con `get_slot(result, "key")`

### Grupo 2: dm_runtime (5 tests) - 15 min
**Archivos**: `tests/unit/test_dm_runtime.py`

**Tests:**
1. `test_execute_flow_with_action_basic`
2. `test_execute_linear_flow_basic`
3. `test_handle_missing_slot`
4. `test_state_isolation_basic`
5. `test_state_persistence_basic`

**Patrón común**:
- Tests usan `DialogueState(slots={...})` constructor
- Reemplazar con `create_empty_state()` + `set_slot()`
- Revisar assertions de estado

### Grupo 3: runtime (6 tests) - 15 min
**Archivos**: `tests/unit/test_runtime.py`

**Tests:**
1. `test_process_message_simple`
2. `test_process_message_updates_state`
3. `test_process_message_handles_nlu_error`
4. `test_process_message_handles_graph_error`
5. `test_process_message_multiple_conversations`
6. `test_process_message_with_checkpoint_loading`

**Patrón común**:
- State creation issues
- Mock configuration
- Assertion updates

### Grupo 4: runtime_context (5 tests) - 10 min
**Archivos**: `tests/unit/test_runtime_context.py`

**Tests:**
1. `test_runtime_context_creation`
2. `test_runtime_context_get_slot_config`
3. `test_runtime_context_get_action_config`
4. `test_runtime_context_get_flow_config`
5. `test_runtime_context_get_slot_config_not_found`
6. `test_dialogue_state_is_serializable`

**Patrón común**:
- `RuntimeContext()` dataclass → `create_runtime_context()`
- State serialization tests

### Grupo 5: runtime_streaming (3 tests) - 10 min
**Archivos**: `tests/unit/test_runtime_streaming.py`

**Tests:**
1. `test_process_message_stream_yields_tokens`
2. `test_process_message_stream_preserves_state`
3. `test_process_message_stream_returns_strings`

**Patrón común**:
- Mock and async streaming setup

### Grupo 6: E2E Integration (5 tests) - 20 min
**Archivos**: `tests/integration/test_e2e.py`

**Tests:**
1. `test_e2e_flight_booking_complete_flow`
2. `test_e2e_slot_correction`
3. `test_e2e_multi_turn_persistence`
4. `test_e2e_multiple_users_isolation`
5. `test_e2e_normalization_integration`

**Patrón común**:
- End-to-end flow verification
- State assertions across multiple turns
- Slot access patterns

### Grupo 7: output_mapping (2 tests) - 10 min
**Archivos**: `tests/integration/test_output_mapping.py`

**Tests:**
1. `test_action_node_applies_map_outputs`
2. `test_action_node_without_map_outputs`

**Patrón común**:
- Action output → slot mapping
- Slot assertions

### Grupo 8: Performance (4 tests) - 15 min
**Archivos**: `tests/performance/test_e2e_performance.py`

**Tests:**
1. `test_e2e_latency_p95`
2. `test_concurrent_throughput`
3. `test_memory_usage`
4. `test_cpu_usage`

**Patrón común**:
- Mock or skip if too slow
- State setup issues

### Grupo 9: du (2 tests) - 10 min
**Archivos**: `tests/unit/test_du.py`

**Tests:**
1. `test_soni_du_forward_with_mock`
2. `test_soni_du_aforward_with_mock`

**Patrón común**:
- DSPy module initialization
- State format

### Grupo 10: Misc (5 tests) - 15 min
**Archivos**: Various

**Tests:**
1. `test_cli_version` - tests/unit/test_cli.py
2. `test_config_manager_load_success` - tests/unit/test_config_manager.py
3. `test_config_manager_load_invalid_schema` - tests/unit/test_config_manager.py
4. `test_config_manager_load_with_mocked_loader` - tests/unit/test_config_manager.py
5. `test_health_endpoint` - tests/unit/test_server_api.py

**Patrón común**:
- Varied issues
- Individual fixes needed

## Estimación Total

| Grupo | Tests | Tiempo |
|-------|-------|--------|
| dm_graph | 4 | 10 min |
| dm_runtime | 5 | 15 min |
| runtime | 6 | 15 min |
| runtime_context | 5 | 10 min |
| runtime_streaming | 3 | 10 min |
| E2E | 5 | 20 min |
| output_mapping | 2 | 10 min |
| Performance | 4 | 15 min |
| DU | 2 | 10 min |
| Misc | 5 | 15 min |
| **TOTAL** | **42** | **~2 horas** |

## Estrategia Recomendada

### Opción 1: Manual Cuidadoso (Recomendado)
Arreglar cada test uno por uno, verificando:
1. State creation pattern
2. Slot access pattern
3. Assertions match schema
4. Imports correctos

**Ventajas**:
- Alta calidad
- Sin introducir errores
- Aprend

er patrones correctos

**Desventajas**:
- Toma más tiempo

### Opción 2: Scripts Iterativos
Crear scripts más pequeños y específicos para cada grupo:
- Un script por grupo de tests
- Probar después de cada script
- Revisar manualmente antes de aplicar

**Ventajas**:
- Más rápido
- Reutilizable

**Desventajas**:
- Riesgo de introducir errores
- Requiere testing cuidadoso

## Patrones Comunes a Arreglar

### 1. State Creation
```python
# ❌ Viejo
state = DialogueState(slots={"origin": "NYC"})

# ✅ Nuevo
state = create_empty_state()
set_slot(state, "origin", "NYC")
```

### 2. Slot Access
```python
# ❌ Viejo
value = state["slots"]["origin"]
assert "destination" in state["slots"]

# ✅ Nuevo
value = get_slot(state, "origin")
assert get_slot(state, "destination") is not None
```

### 3. Field Removal
```python
# ❌ Campo eliminado
assert state["pending_action"] == "book_flight"

# ✅ Campo correcto (según diseño)
assert state.get("nlu_result") is not None
```

### 4. RuntimeContext
```python
# ❌ Viejo
context = RuntimeContext(config=config, scope_manager=sm, ...)

# ✅ Nuevo
context = create_runtime_context(config=config, scope_manager=sm, ...)
```

## Próxima Sesión - Checklist

- [ ] Empezar por Grupo 1 (dm_graph) - 4 tests
- [ ] Verificar cada fix con `uv run pytest tests/unit/test_dm_graph.py`
- [ ] Commit después de cada grupo completado
- [ ] Continuar con Grupo 2 (dm_runtime) - 5 tests
- [ ] Mantener track de progreso con TODOs
- [ ] Final: `uv run pytest tests/` debe dar 557/557

## Documentos de Referencia

- **Schema Autorizado**: `docs/design/04-state-machine.md`
- **Implementación**: `src/soni/core/types.py`
- **Helpers**: `src/soni/core/state.py`

---

**Última actualización**: Diciembre 5, 2025
**Estado**: 515/557 tests passing (92.5%)
**Tiempo estimado para 100%**: ~2 horas de trabajo manual cuidadoso
