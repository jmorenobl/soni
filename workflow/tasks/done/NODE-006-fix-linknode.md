## Task: NODE-006 - Fix LinkNode State Mutation

**ID de tarea:** NODE-006
**Hito:** ADR-002 Alignment
**Dependencias:** Ninguna
**Duración estimada:** 30 minutos

### Objetivo

Eliminar mutación directa del estado en `LinkNode` y añadir `_pending_task: None`.

### Contexto

`LinkNode` muta el estado directamente (`state["flow_stack"] = ...`), lo cual viola el principio de inmutabilidad de LangGraph. Los nodos deben retornar deltas, no mutar estado.

### Entregables

- [ ] Eliminar mutación directa del estado
- [ ] Añadir `_pending_task: None` al return

### Implementación Detallada

#### Paso 1: Eliminar mutación y limpiar _pending_task

**Archivo a modificar:** `src/soni/compiler/nodes/link.py`

**Eliminar líneas 57-58:**
```python
# ELIMINAR:
if pop_delta.flow_stack is not None:
    state["flow_stack"] = pop_delta.flow_stack
```

**Modificar línea 49 para incluir _pending_task:**
```python
updates: dict[str, Any] = {"_flow_changed": True, "_branch_target": "__end__", "_pending_task": None}
```

### Criterios de Éxito

- [ ] No hay mutaciones directas de `state` en `link.py`
- [ ] `_pending_task: None` incluido en return
- [ ] Tests pasan

### Referencias

- [link.py](file:///Users/jorge/Projects/Playground/soni/src/soni/compiler/nodes/link.py)
