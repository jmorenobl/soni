## Task: TASK-004 - Confirm Handlers: Eliminar Mutación de Estado

**ID de tarea:** 004
**Hito:** Architecture Improvements
**Dependencias:** Ninguna
**Duración estimada:** 2 horas
**Prioridad:** CRÍTICA

### Objetivo

Eliminar la mutación directa de `state` en `confirm_handlers.py`, alineando con el patrón inmutable de FlowDelta usado en el resto del framework.

### Contexto

El análisis identificó mutación directa de estado en `confirm_handlers.py:53`:

```python
def apply_delta(state: DialogueState, updates: dict[str, Any], delta: Any) -> None:
    merge_delta(updates, delta)
    if delta and delta.flow_slots is not None:
        state["flow_slots"] = delta.flow_slots  # MUTACIÓN DIRECTA
```

**Problemas:**
1. **Inconsistencia:** FlowManager retorna FlowDelta para tracking inmutable, pero este helper lo rompe
2. **LangGraph:** Puede perder tracking de cambios de estado
3. **Debug difícil:** Cambios de estado ocurren en lugar inesperado
4. **Violación de patrón:** El resto del framework usa updates dict, no mutación directa

### Entregables

- [ ] Eliminar mutación de `state` en `apply_delta()`
- [ ] Actualizar todos los handlers que usan `apply_delta()`
- [ ] Asegurar que confirm_node aplica updates correctamente
- [ ] Verificar que flow slots se propagan correctamente

### Implementación Detallada

#### Paso 1: Modificar apply_delta para NO mutar estado

**Archivo a modificar:** `src/soni/compiler/nodes/confirm_handlers.py`

**Cambiar de:**
```python
def apply_delta(state: DialogueState, updates: dict[str, Any], delta: Any) -> None:
    """Helper to merge delta and apply to state for subsequent operations."""
    from soni.flow.manager import merge_delta

    merge_delta(updates, delta)
    if delta and delta.flow_slots is not None:
        state["flow_slots"] = delta.flow_slots
```

**A:**
```python
def apply_delta(updates: dict[str, Any], delta: FlowDelta | None) -> None:
    """Helper to merge FlowDelta into updates dict.

    Does NOT mutate state - all changes go through updates dict.
    The caller (confirm_node) is responsible for applying updates.

    Args:
        updates: Dict to accumulate state changes
        delta: FlowDelta from FlowManager operation, or None
    """
    from soni.flow.manager import merge_delta

    if delta:
        merge_delta(updates, delta)
```

**Agregar import:**
```python
from soni.flow.manager import FlowDelta
```

#### Paso 2: Actualizar llamadas a apply_delta

**Archivo a modificar:** `src/soni/compiler/nodes/confirm_handlers.py`

**Buscar todas las llamadas y actualizar:**

```python
# Antes (múltiples lugares):
apply_delta(state, updates, delta)

# Después:
apply_delta(updates, delta)
```

**Lugares específicos a modificar:**
- Línea ~65 en AffirmHandler
- Línea ~87 en ModificationHandler
- Línea ~113 en DenyHandler
- Línea ~123 en DenyHandler
- Línea ~125 en DenyHandler

#### Paso 3: Manejar dependencias entre operaciones en mismo turn

**Problema:** Si un handler hace múltiples operaciones de FlowManager, la segunda necesita ver el resultado de la primera.

**Solución en confirm_handlers.py:**

```python
class ModificationHandler:
    """Handler for slot modifications during confirmation."""

    async def handle(
        self,
        ctx: ConfirmationContext,
        state: DialogueState,
        updates: dict[str, Any],
        commands: list[Any],
    ) -> dict[str, Any]:
        """Handle slot modification - update slot and re-prompt."""
        fm = ctx.flow_manager

        # Find set_slot commands
        for cmd in commands:
            if isinstance(cmd, dict) and cmd.get("type") == "set_slot":
                slot_name = cmd.get("slot")
                new_value = cmd.get("value")

                if slot_name and new_value is not None:
                    delta = fm.set_slot(state, slot_name, new_value)
                    apply_delta(updates, delta)

                    # For subsequent operations in this handler,
                    # we need to work with updated state.
                    # Create a working copy with applied delta:
                    if delta and delta.flow_slots is not None:
                        # Use updated slots for subsequent reads
                        working_slots = delta.flow_slots
                    else:
                        working_slots = state.get("flow_slots", {})

        # ... rest of handler using working_slots for reads

        return updates
```

**Nota importante:** La mutación de `state` real ocurre en `confirm_node.py` cuando retorna `updates`.

#### Paso 4: Verificar confirm_node aplica updates

**Archivo a verificar:** `src/soni/compiler/nodes/confirm.py`

Asegurar que el return de confirm_node incluye las keys necesarias:

```python
async def confirm_node(state: DialogueState, config: RunnableConfig) -> dict[str, Any]:
    # ... processing ...

    # Ensure we return all state keys that may have changed
    return {
        "flow_state": updates.get("flow_state", state.get("flow_state")),
        "waiting_for_slot": updates.get("waiting_for_slot"),
        "waiting_for_slot_type": updates.get("waiting_for_slot_type"),
        "response_messages": updates.get("response_messages", []),
        "flow_slots": updates.get("flow_slots", state.get("flow_slots")),
        "flow_stack": updates.get("flow_stack", state.get("flow_stack")),
        **{k: v for k, v in updates.items() if k not in [
            "flow_state", "waiting_for_slot", "waiting_for_slot_type",
            "response_messages", "flow_slots", "flow_stack"
        ]},
    }
```

### TDD Cycle (MANDATORY)

#### Red Phase: Write Failing Tests

**Test file:** `tests/unit/compiler/test_confirm_handlers_immutability.py`

```python
"""Tests verifying confirm handlers don't mutate state."""

import pytest
from unittest.mock import Mock, AsyncMock
from copy import deepcopy

from soni.compiler.nodes.confirm_handlers import (
    apply_delta,
    AffirmHandler,
    ModificationHandler,
    DenyHandler,
)
from soni.flow.manager import FlowDelta


class TestApplyDelta:
    """Test apply_delta helper."""

    def test_does_not_take_state_parameter(self):
        """apply_delta should only take updates and delta."""
        import inspect
        sig = inspect.signature(apply_delta)
        params = list(sig.parameters.keys())

        assert "state" not in params
        assert "updates" in params
        assert "delta" in params

    def test_merges_delta_into_updates(self):
        """Should merge delta fields into updates dict."""
        updates = {}
        delta = FlowDelta(
            flow_slots={"flow_1": {"slot": "value"}},
        )

        apply_delta(updates, delta)

        assert "flow_slots" in updates
        assert updates["flow_slots"]["flow_1"]["slot"] == "value"

    def test_handles_none_delta(self):
        """Should handle None delta gracefully."""
        updates = {"existing": "value"}

        apply_delta(updates, None)

        assert updates == {"existing": "value"}


class TestHandlersDoNotMutateState:
    """Test that handlers don't mutate state directly."""

    @pytest.fixture
    def mock_context(self):
        ctx = Mock()
        ctx.flow_manager = Mock()
        ctx.flow_manager.set_slot = Mock(return_value=FlowDelta(
            flow_slots={"flow_1": {"slot": "new_value"}}
        ))
        ctx.flow_manager.get_all_slots = Mock(return_value={"slot": "value"})
        ctx.slot_name = "test_slot"
        ctx.confirmation_value = "confirmed_value"
        ctx.prompt = "Please confirm"
        return ctx

    @pytest.fixture
    def initial_state(self):
        return {
            "flow_stack": [{"flow_id": "flow_1", "flow_name": "test"}],
            "flow_slots": {"flow_1": {"slot": "original_value"}},
            "messages": [],
        }

    @pytest.mark.asyncio
    async def test_affirm_handler_does_not_mutate_state(self, mock_context, initial_state):
        """AffirmHandler should not mutate state directly."""
        handler = AffirmHandler()
        state_copy = deepcopy(initial_state)
        updates = {}

        await handler.handle(mock_context, initial_state, updates)

        # State should be unchanged
        assert initial_state == state_copy

    @pytest.mark.asyncio
    async def test_modification_handler_does_not_mutate_state(self, mock_context, initial_state):
        """ModificationHandler should not mutate state directly."""
        handler = ModificationHandler()
        state_copy = deepcopy(initial_state)
        updates = {}
        commands = [{"type": "set_slot", "slot": "test", "value": "new"}]

        await handler.handle(mock_context, initial_state, updates, commands)

        # State should be unchanged
        assert initial_state == state_copy

    @pytest.mark.asyncio
    async def test_deny_handler_does_not_mutate_state(self, mock_context, initial_state):
        """DenyHandler should not mutate state directly."""
        handler = DenyHandler()
        state_copy = deepcopy(initial_state)
        updates = {}
        commands = []

        await handler.handle(mock_context, initial_state, updates, commands, None)

        # State should be unchanged
        assert initial_state == state_copy


class TestUpdatesContainChanges:
    """Test that changes are returned in updates dict."""

    @pytest.fixture
    def mock_context(self):
        ctx = Mock()
        ctx.flow_manager = Mock()
        ctx.flow_manager.set_slot = Mock(return_value=FlowDelta(
            flow_slots={"flow_1": {"slot": "new_value"}}
        ))
        ctx.flow_manager.get_all_slots = Mock(return_value={})
        ctx.slot_name = "test_slot"
        ctx.confirmation_value = "confirmed"
        ctx.prompt = "Confirm?"
        return ctx

    @pytest.fixture
    def state(self):
        return {
            "flow_stack": [{"flow_id": "flow_1"}],
            "flow_slots": {"flow_1": {}},
        }

    @pytest.mark.asyncio
    async def test_affirm_handler_returns_updates(self, mock_context, state):
        """AffirmHandler should return slot changes in updates."""
        handler = AffirmHandler()
        updates = {}

        result = await handler.handle(mock_context, state, updates)

        # Should have flow_slots in updates (if delta was applied)
        # The actual assertion depends on handler implementation
        assert isinstance(result, dict)
```

#### Green Phase

Implement the changes and verify:

```bash
uv run pytest tests/unit/compiler/test_confirm_handlers_immutability.py -v
```

### Criterios de Éxito

- [ ] `apply_delta()` no tiene parámetro `state`
- [ ] Ningún handler asigna a `state["flow_slots"]` o `state["flow_stack"]`
- [ ] Tests de inmutabilidad pasan
- [ ] Tests existentes de confirm_node siguen pasando
- [ ] Flujo de confirmación funciona correctamente end-to-end

### Validación Manual

```bash
# Run all confirm-related tests
uv run pytest tests/unit/compiler/test_confirm*.py -v

# Search for state mutations
grep -n "state\[" src/soni/compiler/nodes/confirm_handlers.py
# Should only show reads like state.get(), not assignments

# Run integration test if available
uv run pytest tests/integration/ -k confirm -v
```

### Referencias

- FlowManager FlowDelta pattern: `src/soni/flow/manager.py`
- Análisis original: confirm_handlers state mutation issues
- LangGraph state management: https://langchain-ai.github.io/langgraph/concepts/#state

### Notas Adicionales

- La mutación de estado debe ocurrir SOLO cuando LangGraph aplica el return dict del node
- Si handlers necesitan ver resultados de operaciones previas, deben usar los valores del delta retornado, no mutar state
- Este patrón es consistente con cómo understand_node maneja commands
