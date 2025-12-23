## Task: NODE-002 - Fix CollectNode Legacy Field

**ID de tarea:** NODE-002
**Hito:** ADR-002 Alignment
**Dependencias:** Ninguna
**Duración estimada:** 30 minutos

### Objetivo

Eliminar el campo legacy `_pending_responses` de `CollectNode`.

### Contexto

ADR-002 especifica que solo debe usarse `_pending_task`. El campo `_pending_responses` es legacy y debe eliminarse.

### Entregables

- [ ] Eliminar `_pending_responses` de todos los returns en `collect.py`
- [ ] Tests actualizados si es necesario

### Implementación Detallada

#### Paso 1: Eliminar _pending_responses

**Archivo a modificar:** `src/soni/compiler/nodes/collect.py`

**Líneas a modificar:**
- Línea 62: Eliminar `"_pending_responses": [final_error],`
- Línea 79: Eliminar `"_pending_responses": [prompt],`

### Criterios de Éxito

- [ ] No hay referencias a `_pending_responses` en `collect.py`
- [ ] Tests pasan
- [ ] Linting/mypy pasan

### Referencias

- [ADR-002](file:///Users/jorge/Projects/Playground/soni/workflow/analysis/ADR-002-Human-Input-Gate-Architecture.md)
- [collect.py](file:///Users/jorge/Projects/Playground/soni/src/soni/compiler/nodes/collect.py)
