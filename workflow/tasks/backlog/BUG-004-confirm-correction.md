## Task: BUG-004 - Confirm Correction Flow Issue

**ID de tarea:** BUG-004
**Prioridad:** Media
**Duración estimada:** 1 hora

### Descripción del Bug

El test `test_confirm_correction_updates_slot` falla.

### Causa Probable

El flujo de corrección en `ConfirmNode` (cuando el usuario corrige un slot durante confirmación) puede no estar funcionando correctamente después de los cambios de ADR-002.

Específicamente el `correct_slot` command handler en `confirm_node()` fue modificado para usar `merge_delta()` en vez de acceso directo a `flow_slots`.

### Pasos para Reproducir

```bash
uv run pytest tests/integration/test_m7_confirm.py::test_confirm_correction_updates_slot -v
```

### Archivos Relacionados

- `src/soni/compiler/nodes/confirm.py` (líneas 61-70)
- `tests/integration/test_m7_confirm.py`

### Criterios de Éxito

- [ ] `test_confirm_correction_updates_slot` pasa
- [ ] Corrección de slots durante confirmación funciona
- [ ] El nodo hace loop back a sí mismo con el valor corregido
