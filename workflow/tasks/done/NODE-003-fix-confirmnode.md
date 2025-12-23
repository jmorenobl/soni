## Task: NODE-003 - Fix ConfirmNode ADR-002 Compliance

**ID de tarea:** NODE-003
**Hito:** ADR-002 Alignment
**Dependencias:** Ninguna
**Duración estimada:** 1 hora

### Objetivo

Añadir idempotency check y limpiar campos legacy en `ConfirmNode`.

### Contexto

`ConfirmNode` tiene múltiples problemas de alineamiento con ADR-002:
1. No tiene idempotency check (`_executed_steps`)
2. No limpia `_pending_task: None` en paths de continuación
3. Usa el campo legacy `_pending_responses`

### Entregables

- [ ] Añadir idempotency check al inicio de `confirm_node()`
- [ ] Añadir `_pending_task: None` a todos los returns de continuación
- [ ] Eliminar `_pending_responses`

### Implementación Detallada

#### Paso 1: Añadir idempotency check

**Archivo a modificar:** `src/soni/compiler/nodes/confirm.py`

**Añadir después de línea 23 (después de `slot_name = config.slot`):**
```python
flow_id = fm.get_active_flow_id(state)
step_id = config.step

# Idempotency check
if flow_id:
    executed = (state.get("_executed_steps") or {}).get(flow_id, set())
    if step_id in executed:
        return {"_branch_target": None, "_pending_task": None}
```

#### Paso 2: Limpiar _pending_task en continuations

**Modificar líneas 33, 37, 43-47, 51:**
```python
# Línea 33:
return {"commands": [], "_branch_target": config.on_confirm, "_pending_task": None}

# Línea 37:
return {"commands": [], "_branch_target": config.on_deny, "_pending_task": None}

# Líneas 43-47:
return {
    "flow_slots": delta.flow_slots if delta else {},
    "commands": [],
    "_branch_target": config.step,
    "_pending_task": None,
}

# Línea 51:
return {"_pending_task": None}
```

#### Paso 3: Eliminar _pending_responses

**Línea 72:** Eliminar `"_pending_responses": [prompt],`

### Criterios de Éxito

- [ ] `ConfirmNode` tiene idempotency check
- [ ] Todos los returns incluyen `_pending_task: None` o `_pending_task: confirm(...)`
- [ ] No hay referencias a `_pending_responses`
- [ ] Tests pasan

### Referencias

- [ADR-002](file:///Users/jorge/Projects/Playground/soni/workflow/analysis/ADR-002-Human-Input-Gate-Architecture.md)
- [confirm.py](file:///Users/jorge/Projects/Playground/soni/src/soni/compiler/nodes/confirm.py)
