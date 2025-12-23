## Task: NODE-004 - Fix BranchNode _pending_task Clearing

**ID de tarea:** NODE-004
**Hito:** ADR-002 Alignment
**Dependencias:** Ninguna
**Duración estimada:** 15 minutos

### Objetivo

Añadir `_pending_task: None` al return de `BranchNode`.

### Contexto

ADR-002 requiere que todos los nodos que continúan sin user input limpien `_pending_task`.

### Entregables

- [ ] `BranchNode` retorna `_pending_task: None`

### Implementación Detallada

#### Paso 1: Modificar return

**Archivo a modificar:** `src/soni/compiler/nodes/branch.py`

**Línea 75:**
```python
# Cambiar de:
return {"_branch_target": target}
# A:
return {"_branch_target": target, "_pending_task": None}
```

### Criterios de Éxito

- [ ] `BranchNode` limpia `_pending_task`
- [ ] Tests pasan

### Referencias

- [branch.py](file:///Users/jorge/Projects/Playground/soni/src/soni/compiler/nodes/branch.py)
