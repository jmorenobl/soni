## Task: BUG-001 - Multi-Step Say Flow Interrupts Early

**ID de tarea:** BUG-001
**Prioridad:** Media
**Duración estimada:** 1 hora

### Descripción del Bug

El test `test_multi_step_say` falla porque solo retorna el primer mensaje cuando hay múltiples steps `say` en un flujo.

**Comportamiento esperado:**
```
Hello!
Welcome to Soni!
```

**Comportamiento actual:**
```
Hello!
```

### Causa Probable

El primer `SayNode` retorna `InformTask`, el `PendingTaskHandler` lo envía al sink y retorna `CONTINUE`. Sin embargo, el sink se lee después del primer mensaje y se limpia antes de que el segundo `SayNode` se ejecute.

Posible issue: El orchestrator hace `return` demasiado pronto o el subgraph no continúa al segundo step.

### Pasos para Reproducir

```bash
uv run pytest tests/integration/test_m1_hello_world.py::test_multi_step_say -v
```

### Archivos Relacionados

- `src/soni/dm/nodes/orchestrator.py` (streaming loop)
- `src/soni/compiler/nodes/say.py` (InformTask return)
- `src/soni/runtime/loop.py` (sink collection)

### Criterios de Éxito

- [ ] `test_multi_step_say` pasa
- [ ] Múltiples `say` steps se acumulan en el `MessageSink`
- [ ] Todos los mensajes se retornan juntos
