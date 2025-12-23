## Task: NODE-005 - Fix SetNode _pending_task Clearing

**ID de tarea:** NODE-005
**Hito:** ADR-002 Alignment
**Dependencias:** Ninguna
**Duración estimada:** 15 minutos

### Objetivo

Añadir `_pending_task: None` a todos los returns de `SetNode`.

### Contexto

ADR-002 requiere que todos los nodos que continúan sin user input limpien `_pending_task`.

### Entregables

- [ ] `SetNode` retorna `_pending_task: None` en todos los paths

### Implementación Detallada

#### Paso 1: Modificar returns

**Archivo a modificar:** `src/soni/compiler/nodes/set.py`

**Línea 52:**
```python
return {"_branch_target": None, "_pending_task": None}
```

**Líneas 59-62:**
```python
result: dict[str, Any] = {"_branch_target": None, "_pending_task": None}
if flow_id:
    result["_executed_steps"] = {flow_id: {step_id}}
return result
```

**Línea 77:** Ya tiene `_branch_target`, añadir `_pending_task`:
```python
updates["_branch_target"] = None
updates["_pending_task"] = None
```

### Criterios de Éxito

- [ ] Todos los returns en `SetNode` incluyen `_pending_task: None`
- [ ] Tests pasan

### Referencias

- [set.py](file:///Users/jorge/Projects/Playground/soni/src/soni/compiler/nodes/set.py)
