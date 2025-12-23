## Task: NODE-008 - Fix WhileNode _pending_task Clearing

**ID de tarea:** NODE-008
**Hito:** ADR-002 Alignment
**Dependencias:** Ninguna
**Duración estimada:** 15 minutos

### Objetivo

Añadir `_pending_task: None` a todos los returns de `WhileNode`.

### Contexto

ADR-002 requiere que todos los nodos que continúan sin user input limpien `_pending_task`.

### Entregables

- [ ] `WhileNode` retorna `_pending_task: None` en todos los paths

### Implementación Detallada

#### Paso 1: Modificar returns

**Archivo a modificar:** `src/soni/compiler/nodes/while_loop.py`

**Línea 71:**
```python
return {"_branch_target": loop_body_start, "_pending_task": None}
```

**Línea 75:**
```python
return {"_branch_target": exit_to, "_pending_task": None}
```

**Línea 78:**
```python
return {"_branch_target": None, "_pending_task": None}
```

### Criterios de Éxito

- [ ] Todos los returns en `WhileNode` incluyen `_pending_task: None`
- [ ] Tests pasan

### Referencias

- [while_loop.py](file:///Users/jorge/Projects/Playground/soni/src/soni/compiler/nodes/while_loop.py)
