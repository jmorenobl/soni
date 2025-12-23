## Task: NODE-007 - Fix CallNode _pending_task Clearing

**ID de tarea:** NODE-007
**Hito:** ADR-002 Alignment
**Dependencias:** Ninguna
**Duración estimada:** 15 minutos

### Objetivo

Añadir `_pending_task: None` al return de `CallNode`.

### Contexto

ADR-002 requiere que todos los nodos que continúan sin user input limpien `_pending_task`.

### Entregables

- [ ] `CallNode` retorna `_pending_task: None`

### Implementación Detallada

#### Paso 1: Modificar return

**Archivo a modificar:** `src/soni/compiler/nodes/call.py`

**Línea 49:**
```python
# Cambiar de:
updates: dict[str, Any] = {"_flow_changed": True, "_branch_target": "__end__"}
# A:
updates: dict[str, Any] = {"_flow_changed": True, "_branch_target": "__end__", "_pending_task": None}
```

### Criterios de Éxito

- [ ] `CallNode` limpia `_pending_task`
- [ ] Tests pasan

### Referencias

- [call.py](file:///Users/jorge/Projects/Playground/soni/src/soni/compiler/nodes/call.py)
