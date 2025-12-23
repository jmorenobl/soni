## Task: BUG-003 - Nested Flow Transfer Issues (Link/Call)

**ID de tarea:** BUG-003
**Prioridad:** Alta
**Duración estimada:** 2 horas

### Descripción del Bug

Los tests de flujos anidados fallan:
- `test_link_transfers_control`
- `test_call_returns_to_parent`
- `test_nested_calls`

### Causa Probable

Los nodos `LinkNode` y `CallNode` usan `_flow_changed: True` para señalar cambio de flujo, pero el orchestrator puede no estar manejando correctamente la transición entre subgraphs.

También se eliminó la mutación directa de estado en `LinkNode` (NODE-006) lo cual podría afectar el flow stack.

### Pasos para Reproducir

```bash
uv run pytest tests/integration/test_m6_nested.py -v
```

### Archivos Relacionados

- `src/soni/compiler/nodes/link.py`
- `src/soni/compiler/nodes/call.py`
- `src/soni/dm/nodes/orchestrator.py`
- `src/soni/flow/manager.py`

### Criterios de Éxito

- [ ] `test_link_transfers_control` pasa
- [ ] `test_call_returns_to_parent` pasa
- [ ] `test_nested_calls` pasa
- [ ] Flow stack se gestiona correctamente entre subgraphs
