## Task: BUG-002 - ActionRegistry.register() API Mismatch

**ID de tarea:** BUG-002
**Prioridad:** Media
**Duración estimada:** 30 minutos

### Descripción del Bug

Los tests `test_action_executes_and_maps_outputs` y `test_action_registry_contains` fallan con:

```
TypeError: ActionRegistry.register() takes 2 positional arguments but 3 were given
```

### Causa Probable

La API de `ActionRegistry.register()` cambió pero los tests no se actualizaron.

### Pasos para Reproducir

```bash
uv run pytest tests/integration/test_m5_action.py -v
```

### Archivos Relacionados

- `src/soni/actions/registry.py`
- `tests/integration/test_m5_action.py`

### Criterios de Éxito

- [ ] `test_action_executes_and_maps_outputs` pasa
- [ ] `test_action_registry_contains` pasa
- [ ] API de `ActionRegistry.register()` es consistente
