## Task: NODE-001 - Fix SayNode ADR-002 Compliance

**ID de tarea:** NODE-001
**Hito:** ADR-002 Alignment
**Dependencias:** Ninguna
**Duración estimada:** 1 hora

### Objetivo

Revertir `SayNode` para usar `InformTask` en lugar de `message_sink.send()` directo, alineándolo con ADR-002.

### Contexto

ADR-002 especifica que todos los mensajes deben pasar por el patrón `PendingTask`. Actualmente `SayNode` bypasea esto usando `message_sink.send()` directamente, lo cual:
- Impide al orchestrator rastrear el ciclo de vida del mensaje
- Rompe la consistencia arquitectónica
- Fue un workaround de debugging, no una decisión de diseño

### Entregables

- [ ] `SayNode` retorna `InformTask` con `wait_for_ack=False`
- [ ] Añadir `_pending_task: None` cuando se salta por idempotency
- [ ] Tests actualizados

### Implementación Detallada

#### Paso 1: Revertir a InformTask

**Archivo a modificar:** `src/soni/compiler/nodes/say.py`

**Código actual (líneas 61-63):**
```python
if final_message:
    await runtime.context.message_sink.send(final_message)
```

**Código nuevo:**
```python
from soni.core.pending_task import inform

# En say_node():
if final_message:
    result["_pending_task"] = inform(
        prompt=final_message,
        wait_for_ack=False,
    )
```

#### Paso 2: Limpiar _pending_task en idempotency skip

**Línea 42:**
```python
# Cambiar de:
return {"_branch_target": None}
# A:
return {"_branch_target": None, "_pending_task": None}
```

### Exception: Test-After

**Reason for test-after:**
- [x] Legacy code retrofit

**Justification:**
El código ya existe y funciona. Esta es una corrección de alineamiento arquitectónico.

### Criterios de Éxito

- [ ] `SayNode` retorna `InformTask` en vez de llamar `message_sink` directamente
- [ ] No hay llamadas a `message_sink.send()` en `say.py`
- [ ] Tests pasan
- [ ] Linting/mypy pasan

### Validación Manual

```bash
uv run soni chat --config examples/banking/domain --module examples.banking.handlers
# Verificar que los mensajes "say" aparecen correctamente
```

### Referencias

- [ADR-002](file:///Users/jorge/Projects/Playground/soni/workflow/analysis/ADR-002-Human-Input-Gate-Architecture.md)
- [say.py](file:///Users/jorge/Projects/Playground/soni/src/soni/compiler/nodes/say.py)
