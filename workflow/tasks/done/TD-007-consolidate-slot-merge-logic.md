## Task: TD-007 - Consolidate Duplicate Slot Merge Logic

**ID de tarea:** TD-007
**Fase:** Phase 3 - Consolidation
**Prioridad:** 🟡 MEDIUM
**Dependencias:** TD-006 (opcional, pero recomendado completar primero)
**Duración estimada:** 1-2 horas

### Objetivo

Consolidar la lógica duplicada de merge de `flow_slots` que aparece en 4+ ubicaciones en una única función autoritativa, siguiendo el principio DRY.

### Contexto

El mismo patrón de merge para `flow_slots` se repite en múltiples lugares:

| Archivo | Función/Ubicación |
|---------|-------------------|
| `core/types.py` | `_merge_flow_slots()` reducer |
| `dm/nodes/orchestrator.py` | `_merge_outputs()` |
| `dm/orchestrator/command_processor.py` | inline en `process()` |
| `flow/manager.py` | `merge_delta()` |

**Impacto:** Bug fixes deben aplicarse en múltiples lugares. Riesgo de comportamiento inconsistente.

### Entregables

- [ ] Crear función `deep_merge_flow_slots()` en `core/slot_utils.py`
- [ ] Reemplazar todas las implementaciones duplicadas con la nueva función
- [ ] Añadir tests exhaustivos para la función consolidada
- [ ] Documentar edge cases y comportamiento esperado

### Implementación Detallada

#### Paso 1: Crear función autoritativa en core/slot_utils.py

**Archivo a crear:** `src/soni/core/slot_utils.py`

```python
"""Utilities for slot manipulation.

This module provides the single source of truth for slot-related operations.
"""

from typing import Any
from copy import deepcopy


def deep_merge_flow_slots(
    base: dict[str, dict[str, Any]],
    new: dict[str, dict[str, Any]],
    *,
    in_place: bool = False,
) -> dict[str, dict[str, Any]]:
    """Merge flow slot dictionaries with deep merge for nested values.

    This is the **single source of truth** for flow_slots merging.
    All other merge implementations should delegate to this function.

    Args:
        base: Base flow_slots dictionary {flow_id: {slot_name: value}}
        new: New values to merge into base
        in_place: If True, mutates base. If False, returns new dict.

    Returns:
        Merged dictionary with new values overriding base values.
        For matching flow_ids, slot values are merged (not replaced).

    Example:
        >>> base = {"flow1": {"slot_a": 1, "slot_b": 2}}
        >>> new = {"flow1": {"slot_b": 3, "slot_c": 4}, "flow2": {"slot_x": 5}}
        >>> deep_merge_flow_slots(base, new)
        {
            "flow1": {"slot_a": 1, "slot_b": 3, "slot_c": 4},
            "flow2": {"slot_x": 5}
        }

    Notes:
        - New flow_ids are added to the result
        - For existing flow_ids, slots are merged (not replaced)
        - Individual slot values are replaced (not deep merged)
        - None values in new dict DO overwrite base values
    """
    if not new:
        return base if in_place else dict(base)

    result = base if in_place else deepcopy(base)

    for flow_id, slots in new.items():
        if flow_id in result:
            # Merge slots for existing flow
            result[flow_id] = {**result[flow_id], **slots}
        else:
            # Add new flow
            result[flow_id] = dict(slots)

    return result


def get_slot_value(
    flow_slots: dict[str, dict[str, Any]],
    flow_id: str,
    slot_name: str,
    default: Any = None,
) -> Any:
    """Get a slot value safely with default.

    Args:
        flow_slots: Flow slots dictionary
        flow_id: Flow instance ID
        slot_name: Name of the slot
        default: Value to return if not found

    Returns:
        Slot value or default
    """
    return flow_slots.get(flow_id, {}).get(slot_name, default)


def set_slot_value(
    flow_slots: dict[str, dict[str, Any]],
    flow_id: str,
    slot_name: str,
    value: Any,
) -> dict[str, dict[str, Any]]:
    """Set a slot value immutably.

    Args:
        flow_slots: Flow slots dictionary
        flow_id: Flow instance ID
        slot_name: Name of the slot
        value: Value to set

    Returns:
        New flow_slots dict with updated value
    """
    result = deepcopy(flow_slots)
    if flow_id not in result:
        result[flow_id] = {}
    result[flow_id][slot_name] = value
    return result
```

#### Paso 2: Actualizar core/types.py

**Archivo a modificar:** `src/soni/core/types.py`

```python
# Antes:
def _merge_flow_slots(
    current: dict[str, dict[str, Any]] | None,
    new: dict[str, dict[str, Any]] | None,
) -> dict[str, dict[str, Any]]:
    # ... implementación duplicada

# Después:
from soni.core.slot_utils import deep_merge_flow_slots

def _merge_flow_slots(
    current: dict[str, dict[str, Any]] | None,
    new: dict[str, dict[str, Any]] | None,
) -> dict[str, dict[str, Any]]:
    """Reducer for flow_slots in LangGraph state."""
    if current is None:
        return new or {}
    if new is None:
        return current
    return deep_merge_flow_slots(current, new)
```

#### Paso 3: Actualizar flow/manager.py

**Archivo a modificar:** `src/soni/flow/manager.py`

```python
# En merge_delta():
from soni.core.slot_utils import deep_merge_flow_slots

def merge_delta(updates: dict[str, Any], delta: FlowDelta | None) -> None:
    if delta is None:
        return

    if delta.flow_stack is not None:
        updates["flow_stack"] = delta.flow_stack

    if delta.flow_slots is not None:
        existing = updates.get("flow_slots", {})
        updates["flow_slots"] = deep_merge_flow_slots(existing, delta.flow_slots)
```

#### Paso 4: Actualizar orchestrator y command_processor

**Archivos a modificar:**
- `src/soni/dm/nodes/orchestrator.py`
- `src/soni/dm/orchestrator/command_processor.py`

Reemplazar lógica inline de merge con llamadas a `deep_merge_flow_slots`.

### TDD Cycle

#### Red Phase: Write Failing Tests

**Test file:** `tests/unit/core/test_slot_utils.py`

```python
"""Tests for slot utilities."""

import pytest
from soni.core.slot_utils import (
    deep_merge_flow_slots,
    get_slot_value,
    set_slot_value,
)


class TestDeepMergeFlowSlots:
    """Tests for deep_merge_flow_slots function."""

    def test_merge_empty_new_returns_base(self):
        """Test merging empty new dict returns base unchanged."""
        base = {"flow1": {"slot": "value"}}
        result = deep_merge_flow_slots(base, {})
        assert result == base

    def test_merge_empty_base_returns_new(self):
        """Test merging into empty base returns copy of new."""
        new = {"flow1": {"slot": "value"}}
        result = deep_merge_flow_slots({}, new)
        assert result == new

    def test_merge_adds_new_flow_ids(self):
        """Test that new flow_ids are added."""
        base = {"flow1": {"slot1": "a"}}
        new = {"flow2": {"slot2": "b"}}
        result = deep_merge_flow_slots(base, new)
        assert "flow1" in result
        assert "flow2" in result

    def test_merge_combines_slots_for_same_flow(self):
        """Test slots are merged for same flow_id."""
        base = {"flow1": {"slot_a": 1}}
        new = {"flow1": {"slot_b": 2}}
        result = deep_merge_flow_slots(base, new)
        assert result["flow1"] == {"slot_a": 1, "slot_b": 2}

    def test_merge_new_overwrites_existing_slot(self):
        """Test new slot values overwrite existing."""
        base = {"flow1": {"slot": "old"}}
        new = {"flow1": {"slot": "new"}}
        result = deep_merge_flow_slots(base, new)
        assert result["flow1"]["slot"] == "new"

    def test_merge_does_not_mutate_base_by_default(self):
        """Test base is not mutated when in_place=False."""
        base = {"flow1": {"slot": "value"}}
        original_base = {"flow1": {"slot": "value"}}
        deep_merge_flow_slots(base, {"flow1": {"new": "value"}})
        assert base == original_base

    def test_merge_mutates_base_when_in_place(self):
        """Test base is mutated when in_place=True."""
        base = {"flow1": {"slot": "value"}}
        result = deep_merge_flow_slots(base, {"flow1": {"new": "x"}}, in_place=True)
        assert base is result
        assert "new" in base["flow1"]

    def test_none_values_overwrite(self):
        """Test None values in new overwrite base values."""
        base = {"flow1": {"slot": "value"}}
        new = {"flow1": {"slot": None}}
        result = deep_merge_flow_slots(base, new)
        assert result["flow1"]["slot"] is None


class TestGetSlotValue:
    """Tests for get_slot_value function."""

    def test_returns_value_when_exists(self):
        """Test returns slot value when present."""
        slots = {"flow1": {"my_slot": "value"}}
        assert get_slot_value(slots, "flow1", "my_slot") == "value"

    def test_returns_default_when_flow_missing(self):
        """Test returns default when flow_id not found."""
        slots = {"flow1": {"slot": "value"}}
        assert get_slot_value(slots, "flow2", "slot", "default") == "default"

    def test_returns_default_when_slot_missing(self):
        """Test returns default when slot_name not found."""
        slots = {"flow1": {"slot": "value"}}
        assert get_slot_value(slots, "flow1", "other", "default") == "default"


class TestSetSlotValue:
    """Tests for set_slot_value function."""

    def test_sets_value_in_existing_flow(self):
        """Test setting slot in existing flow."""
        slots = {"flow1": {"existing": "value"}}
        result = set_slot_value(slots, "flow1", "new_slot", "new_value")
        assert result["flow1"]["new_slot"] == "new_value"
        assert result["flow1"]["existing"] == "value"

    def test_creates_flow_if_not_exists(self):
        """Test creates flow_id if not present."""
        result = set_slot_value({}, "flow1", "slot", "value")
        assert result == {"flow1": {"slot": "value"}}

    def test_does_not_mutate_original(self):
        """Test original dict is not mutated."""
        original = {"flow1": {"slot": "old"}}
        set_slot_value(original, "flow1", "slot", "new")
        assert original["flow1"]["slot"] == "old"
```

**Verify tests fail:**
```bash
uv run pytest tests/unit/core/test_slot_utils.py -v
# Expected: FAILED (module doesn't exist yet)
```

#### Green Phase: Make Tests Pass

Implement the module as described.

```bash
uv run pytest tests/unit/core/test_slot_utils.py -v
# Expected: PASSED ✅
```

### Criterios de Éxito

- [ ] Single `deep_merge_flow_slots` function in `core/slot_utils.py`
- [ ] All 4+ duplicated implementations replaced
- [ ] Comprehensive tests covering edge cases
- [ ] All existing tests pass
- [ ] `uv run mypy src/soni/core/slot_utils.py` passes
- [ ] `uv run ruff check src/soni/` passes

### Validación Manual

**Comandos para validar:**

```bash
# Search for remaining inline implementations
rg "flow_slots\[" src/soni/ --context 2

# Verify the new module is used
rg "deep_merge_flow_slots" src/soni/

# Run full test suite
uv run pytest tests/ -v

# Type check
uv run mypy src/soni/
```

**Resultado esperado:**
- No more inline merge implementations
- All merge calls go through `deep_merge_flow_slots`
- All tests pass

### Referencias

- [Technical Debt Analysis](file:///Users/jorge/Projects/Playground/soni/workflow/analysis/technical-debt-analysis.md#L125-151)
- [DRY Principle](https://en.wikipedia.org/wiki/Don%27t_repeat_yourself)

### Notas Adicionales

- El parámetro `in_place` permite optimización cuando se sabe que el dict base no será usado más
- Considerar si `deepcopy` es necesario o si shallow copy es suficiente para performance
- Las funciones adicionales `get_slot_value` y `set_slot_value` son bonus utilities
- Este cambio es backward-compatible - la API externa no cambia
