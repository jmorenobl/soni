## Task: BUG-005 - NLU Empty Message Handling

**ID de tarea:** BUG-005
**Prioridad:** Baja
**Duración estimada:** 15 minutos

### Descripción del Bug

El test `test_nlu_empty_message_returns_no_commands` falla.

### Pasos para Reproducir

```bash
uv run pytest tests/integration/test_m4_nlu.py::test_nlu_empty_message_returns_no_commands -v
```

### Archivos Relacionados

- `src/soni/dm/nodes/understand.py`
- `tests/integration/test_m4_nlu.py`

### Criterios de Éxito

- [ ] `test_nlu_empty_message_returns_no_commands` pasa
