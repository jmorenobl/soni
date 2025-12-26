## Task: TD-008 - Unify merge_delta APIs

**ID de tarea:** TD-008
**Fase:** Phase 3 - Consolidation
**Prioridad:** 🟡 MEDIUM
**Dependencias:** TD-007 (recomendado)
**Duración estimada:** 30 minutos

### Objetivo

Unificar las dos APIs de merge_delta con nombres similares pero comportamientos diferentes para eliminar confusión y mejorar la mantenibilidad.

### Contexto

Existen dos funciones con nombres muy similares pero APIs diferentes:

```python
# core/types.py - Combina múltiples deltas en uno
def merge_deltas(deltas: list[FlowDelta]) -> FlowDelta:
    """Merge multiple deltas into one."""

# flow/manager.py - Muta un dict de updates con un delta
def merge_delta(updates: dict[str, Any], delta: FlowDelta | None) -> None:
    """Mutates updates dict with delta contents."""
```

**Impacto:** Confusión para desarrolladores. Fácil usar la función incorrecta.

### Entregables

- [ ] Renombrar `flow/manager.py::merge_delta` a `apply_delta_to_dict`
- [ ] O consolidar en método `FlowDelta.apply_to(updates: dict)`
- [ ] Actualizar todos los call sites
- [ ] Documentar claramente la diferencia entre las APIs

### Implementación Detallada

#### Opción A: Renombrar a `apply_delta_to_dict` (Recomendada)

**Archivo a modificar:** `src/soni/flow/manager.py`

```python
# Antes:
def merge_delta(updates: dict[str, Any], delta: FlowDelta | None) -> None:
    """Mutates updates dict with delta contents."""
    ...

# Después:
def apply_delta_to_dict(updates: dict[str, Any], delta: FlowDelta | None) -> None:
    """Apply a FlowDelta to an updates dictionary in-place.

    This function mutates the updates dict, adding flow_stack and flow_slots
    from the delta.

    Args:
        updates: Dictionary to update (mutated in place)
        delta: FlowDelta to apply, or None (no-op)

    Note:
        This is different from core.types.merge_deltas() which combines
        multiple FlowDelta objects into a single FlowDelta.
    """
    if delta is None:
        return

    if delta.flow_stack is not None:
        updates["flow_stack"] = delta.flow_stack

    if delta.flow_slots is not None:
        from soni.core.slot_utils import deep_merge_flow_slots
        existing = updates.get("flow_slots", {})
        updates["flow_slots"] = deep_merge_flow_slots(existing, delta.flow_slots)


# Mantener alias para backward compatibility (deprecar)
def merge_delta(updates: dict[str, Any], delta: FlowDelta | None) -> None:
    """Deprecated: Use apply_delta_to_dict instead."""
    import warnings
    warnings.warn(
        "merge_delta is deprecated, use apply_delta_to_dict",
        DeprecationWarning,
        stacklevel=2,
    )
    apply_delta_to_dict(updates, delta)
```

#### Opción B: Consolidar en método FlowDelta.apply_to

**Archivo a modificar:** `src/soni/core/types.py`

```python
@dataclass
class FlowDelta:
    """Delta for flow state changes."""
    flow_stack: list[FlowContext] | None = None
    flow_slots: dict[str, dict[str, Any]] | None = None

    def apply_to(self, updates: dict[str, Any]) -> None:
        """Apply this delta to an updates dictionary in-place.

        Args:
            updates: Dictionary to update (mutated in place)
        """
        if self.flow_stack is not None:
            updates["flow_stack"] = self.flow_stack

        if self.flow_slots is not None:
            from soni.core.slot_utils import deep_merge_flow_slots
            existing = updates.get("flow_slots", {})
            updates["flow_slots"] = deep_merge_flow_slots(existing, self.flow_slots)
```

**Uso:**
```python
# Antes:
merge_delta(updates, delta)

# Después:
if delta:
    delta.apply_to(updates)
```

#### Paso 2: Actualizar call sites

**Buscar y reemplazar:**
```bash
rg "from soni.flow.manager import.*merge_delta" src/
rg "merge_delta\(" src/soni/ --context 1
```

**Para cada call site:**
- Cambiar import a `apply_delta_to_dict`
- O usar `delta.apply_to(updates)` si se eligió Opción B

### Exception: Test-After

**Reason for test-after:**
- [x] Legacy code retrofit

**Justification:**
Este es un renaming que no cambia lógica. Los tests existentes validan comportamiento.

### Criterios de Éxito

- [ ] APIs claramente diferenciadas por nombre
- [ ] Todos los call sites actualizados
- [ ] Deprecation warning en función antigua (si se mantiene)
- [ ] Tests existentes pasan
- [ ] Documentación actualizada

### Validación Manual

**Comandos para validar:**

```bash
# Verificar que no quedan usos de merge_delta (excepto deprecation)
rg "merge_delta\(" src/soni/ --line-number

# Verificar nuevos usos
rg "apply_delta_to_dict\(" src/soni/
# O
rg "\.apply_to\(" src/soni/

# Tests
uv run pytest tests/ -v
```

### Referencias

- [Technical Debt Analysis](file:///Users/jorge/Projects/Playground/soni/workflow/analysis/technical-debt-analysis.md#L153-175)
- [Naming is Hard](https://martinfowler.com/bliki/TwoHardThings.html)

### Notas Adicionales

- Preferir Opción A si se quiere mantener funciones standalone
- Preferir Opción B si se quiere un API más OOP orientado
- El alias deprecado puede eliminarse en v1.0
