## Task: TD-006 - Extract Orchestrator Helpers to state_utils.py

**ID de tarea:** TD-006
**Fase:** Phase 2 - Structure
**Prioridad:** 🔴 HIGH
**Dependencias:** Ninguna
**Duración estimada:** 1-2 horas

### Objetivo

Extraer las 5 funciones helper del archivo `orchestrator.py` a un módulo dedicado `state_utils.py` para mejorar la organización, reusabilidad y testabilidad.

### Contexto

El archivo `orchestrator.py` contiene 232 líneas con funciones helper mezcladas con la lógica principal del nodo:
- `_merge_state`
- `_build_subgraph_state`
- `_transform_result`
- `_merge_outputs`
- `_build_merged_return`

Estas helpers no son reutilizables en otros contextos y testearlas requiere importar todo el módulo.

**Archivo afectado:** [dm/nodes/orchestrator.py](file:///Users/jorge/Projects/Playground/soni/src/soni/dm/nodes/orchestrator.py)

### Entregables

- [ ] Crear `src/soni/dm/orchestrator/state_utils.py` con las funciones extraídas
- [ ] Añadir exports a `src/soni/dm/orchestrator/__init__.py`
- [ ] Actualizar imports en `orchestrator.py`
- [ ] Crear tests unitarios para cada función
- [ ] Reducir `orchestrator.py` a ~150 líneas o menos

### Implementación Detallada

#### Paso 1: Crear el módulo state_utils.py

**Archivo a crear:** `src/soni/dm/orchestrator/state_utils.py`

```python
"""State manipulation utilities for orchestrator.

This module provides pure functions for merging and transforming
state dictionaries during orchestration.
"""

from typing import Any


def merge_state(base: dict[str, Any], delta: dict[str, Any]) -> dict[str, Any]:
    """Merge delta into base state dict.

    Performs a shallow merge with delta values overriding base values.

    Args:
        base: Base state dictionary
        delta: Changes to merge into base

    Returns:
        New dictionary with merged values

    Example:
        >>> merge_state({"a": 1, "b": 2}, {"b": 3, "c": 4})
        {"a": 1, "b": 3, "c": 4}
    """
    result = dict(base)
    result.update(delta)
    return result


def build_subgraph_state(state: dict[str, Any]) -> dict[str, Any]:
    """Build initial state for subgraph execution.

    Extracts relevant fields from parent state to pass to subgraph.

    Args:
        state: Parent dialogue state

    Returns:
        State dict suitable for subgraph input
    """
    # Extract only fields needed by subgraph
    return {
        "messages": state.get("messages", []),
        "flow_stack": state.get("flow_stack", []),
        "flow_slots": state.get("flow_slots", {}),
        # Add other relevant fields
    }


def transform_result(result: dict[str, Any]) -> dict[str, Any]:
    """Transform subgraph result to parent-compatible format.

    Converts subgraph output format to match parent state expectations.

    Args:
        result: Subgraph execution result

    Returns:
        Transformed result compatible with parent state
    """
    # Transform as needed
    return dict(result)


def merge_outputs(target: dict[str, Any], source: dict[str, Any]) -> None:
    """Merge source outputs into target dict in-place.

    Performs deep merge for nested dicts like flow_slots.

    Args:
        target: Target dict to update (mutated in place)
        source: Source dict with values to merge

    Note:
        This function mutates target. For immutable version,
        use merge_state().
    """
    for key, value in source.items():
        if key in target and isinstance(target[key], dict) and isinstance(value, dict):
            # Deep merge for dicts
            target[key] = {**target[key], **value}
        else:
            target[key] = value


def build_merged_return(
    updates: dict[str, Any],
    final_output: dict[str, Any],
    pending_task: Any | None,
) -> dict[str, Any]:
    """Build final return dict from orchestrator node.

    Combines accumulated updates with final output and pending task.

    Args:
        updates: Accumulated state updates
        final_output: Final output from processing
        pending_task: Optional pending task for interruption

    Returns:
        Complete return dict for LangGraph
    """
    result = dict(updates)
    merge_outputs(result, final_output)
    if pending_task is not None:
        result["pending_task"] = pending_task
    return result
```

#### Paso 2: Actualizar __init__.py

**Archivo a modificar:** `src/soni/dm/orchestrator/__init__.py`

```python
"""Orchestrator module."""

from soni.dm.orchestrator.state_utils import (
    merge_state,
    build_subgraph_state,
    transform_result,
    merge_outputs,
    build_merged_return,
)

__all__ = [
    "merge_state",
    "build_subgraph_state",
    "transform_result",
    "merge_outputs",
    "build_merged_return",
]
```

#### Paso 3: Actualizar orchestrator.py

**Archivo a modificar:** `src/soni/dm/nodes/orchestrator.py`

```python
# Antes (funciones definidas inline):
def _merge_state(...): ...
def _build_subgraph_state(...): ...
# ...

# Después (importadas):
from soni.dm.orchestrator import (
    merge_state,
    build_subgraph_state,
    transform_result,
    merge_outputs,
    build_merged_return,
)

# Uso sin underscore prefix ya que son públicas
result = merge_state(base, delta)
```

### TDD Cycle

#### Red Phase: Write Failing Tests

**Test file:** `tests/unit/dm/orchestrator/test_state_utils.py`

```python
"""Tests for orchestrator state utilities."""

import pytest
from soni.dm.orchestrator.state_utils import (
    merge_state,
    build_subgraph_state,
    transform_result,
    merge_outputs,
    build_merged_return,
)


class TestMergeState:
    """Tests for merge_state function."""

    def test_merge_state_overwrites_existing_keys(self):
        """Test that delta values override base values."""
        base = {"a": 1, "b": 2}
        delta = {"b": 3}
        result = merge_state(base, delta)
        assert result == {"a": 1, "b": 3}

    def test_merge_state_adds_new_keys(self):
        """Test that new keys from delta are added."""
        base = {"a": 1}
        delta = {"b": 2}
        result = merge_state(base, delta)
        assert result == {"a": 1, "b": 2}

    def test_merge_state_does_not_mutate_inputs(self):
        """Test that input dicts are not modified."""
        base = {"a": 1}
        delta = {"b": 2}
        merge_state(base, delta)
        assert base == {"a": 1}
        assert delta == {"b": 2}


class TestBuildSubgraphState:
    """Tests for build_subgraph_state function."""

    def test_extracts_required_fields(self):
        """Test that required fields are extracted."""
        state = {
            "messages": [{"role": "user", "content": "hi"}],
            "flow_stack": [{"flow_id": "test"}],
            "flow_slots": {"test": {"slot": "value"}},
            "extra_field": "ignored",
        }
        result = build_subgraph_state(state)
        assert "messages" in result
        assert "flow_stack" in result
        assert "flow_slots" in result

    def test_handles_missing_fields(self):
        """Test that missing fields get defaults."""
        result = build_subgraph_state({})
        assert result.get("messages") == []
        assert result.get("flow_stack") == []


class TestMergeOutputs:
    """Tests for merge_outputs function."""

    def test_merges_simple_values(self):
        """Test merging simple key-value pairs."""
        target = {"a": 1}
        source = {"b": 2}
        merge_outputs(target, source)
        assert target == {"a": 1, "b": 2}

    def test_deep_merges_nested_dicts(self):
        """Test that nested dicts are deep merged."""
        target = {"flow_slots": {"flow1": {"slot1": "a"}}}
        source = {"flow_slots": {"flow1": {"slot2": "b"}}}
        merge_outputs(target, source)
        assert target["flow_slots"]["flow1"] == {"slot1": "a", "slot2": "b"}


class TestBuildMergedReturn:
    """Tests for build_merged_return function."""

    def test_combines_updates_and_output(self):
        """Test combining updates with final output."""
        updates = {"key1": "value1"}
        final_output = {"key2": "value2"}
        result = build_merged_return(updates, final_output, None)
        assert result == {"key1": "value1", "key2": "value2"}

    def test_includes_pending_task_when_present(self):
        """Test pending task is included when not None."""
        pending = {"task": "data"}
        result = build_merged_return({}, {}, pending)
        assert result["pending_task"] == pending
```

**Verify tests fail:**
```bash
uv run pytest tests/unit/dm/orchestrator/test_state_utils.py -v
# Expected: FAILED (module doesn't exist yet)
```

#### Green Phase: Make Tests Pass

Implement the module as described in Implementación Detallada.

```bash
uv run pytest tests/unit/dm/orchestrator/test_state_utils.py -v
# Expected: PASSED ✅
```

### Criterios de Éxito

- [ ] `orchestrator.py` reduced to ~150 LOC or less
- [ ] New `state_utils.py` module with 5 functions
- [ ] All functions have comprehensive docstrings
- [ ] All existing tests still pass
- [ ] New unit tests for each function
- [ ] `uv run mypy src/soni/dm/orchestrator/` passes
- [ ] `uv run ruff check src/soni/dm/` passes

### Validación Manual

**Comandos para validar:**

```bash
# Verify file sizes
wc -l src/soni/dm/nodes/orchestrator.py
wc -l src/soni/dm/orchestrator/state_utils.py

# Run all tests
uv run pytest tests/ -v

# Run specific orchestrator tests
uv run pytest tests/unit/dm/orchestrator/ -v

# Type check
uv run mypy src/soni/dm/

# Lint
uv run ruff check src/soni/dm/
```

**Resultado esperado:**
- orchestrator.py < 160 LOC
- state_utils.py exists with tests
- All tests pass

### Referencias

- [Technical Debt Analysis](file:///Users/jorge/Projects/Playground/soni/workflow/analysis/technical-debt-analysis.md#L51-70)
- [Extract Function Refactoring](https://refactoring.com/catalog/extractFunction.html)

### Notas Adicionales

- Las funciones extraídas son ahora públicas (sin underscore) ya que son parte del API del módulo
- Considerar si `merge_outputs` debería ser inmutable como `merge_state`
- Estos utilities pueden ser útiles en otros contextos de la aplicación
- Mantener tests de integración existentes para validar comportamiento end-to-end
