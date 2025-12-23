# Task: HIG-004 - Subgraph Migration

**ID de tarea:** HIG-004
**Hito:** Human Input Gate Refactoring (ADR-002)
**Dependencias:** HIG-001, HIG-003
**Duración estimada:** 2 días

## Objetivo

Migrar los nodos de subgraph (`collect_node`, `confirm_node`, `action_node`) para que usen las nuevas factory functions de PendingTask y retornen tareas en lugar de llamar a `interrupt()` directamente.

## Contexto

Los subgraphs actuales llaman a `interrupt()` directamente, lo que acopla la lógica de interrupts al subgraph. Con la nueva arquitectura, los subgraphs retornan `PendingTask` y el orchestrator decide si interrumpir. Esto mejora testabilidad y separación de responsabilidades.

**Referencia:** [ADR-002](../analysis/ADR-002-Human-Input-Gate-Architecture.md) - Sección 4

## Entregables

- [ ] Modificar `collect_node` para usar `collect()` factory
- [ ] Modificar `confirm_node` para usar `confirm()` factory
- [ ] Modificar `action_node` para usar `inform()` factory
- [ ] Actualizar subgraph builder si es necesario
- [ ] Eliminar código obsoleto de interrupt directo
- [ ] Tests con mocks para verificar comportamiento

---

## TDD Cycle (MANDATORY)

### Red Phase: Write Failing Tests

**Test file:** `tests/unit/compiler/test_subgraph_nodes.py`

```python
"""Tests for migrated subgraph nodes using PendingTask."""
import pytest
from unittest.mock import MagicMock, AsyncMock

from soni.core.pending_task import is_collect, is_confirm, is_inform


class TestCollectNode:
    """Tests for collect_node returning PendingTask."""

    @pytest.mark.asyncio
    async def test_collect_returns_pending_task_when_slot_empty(self):
        """Test that collect_node returns CollectTask when slot is empty."""
        # Arrange
        from soni.compiler.nodes.collect import collect_node

        config = MagicMock()
        config.slot = "amount"
        config.message = "Enter amount:"

        state = {
            "flow_slots": {},  # Empty slots
            "user_message": None,
        }
        runtime = MagicMock()

        # Act
        result = await collect_node(state, runtime, config)

        # Assert
        assert "_pending_task" in result
        task = result["_pending_task"]
        assert is_collect(task)
        assert task["slot"] == "amount"
        assert task["prompt"] == "Enter amount:"

    @pytest.mark.asyncio
    async def test_collect_returns_empty_when_slot_filled(self):
        """Test that collect_node returns empty dict when slot has value."""
        # Arrange
        from soni.compiler.nodes.collect import collect_node

        config = MagicMock()
        config.slot = "amount"

        state = {
            "flow_slots": {"amount": "500"},  # Slot has value
        }
        runtime = MagicMock()

        # Act
        result = await collect_node(state, runtime, config)

        # Assert
        assert "_pending_task" not in result or result.get("_pending_task") is None

    @pytest.mark.asyncio
    async def test_collect_does_not_call_interrupt(self):
        """Test that collect_node does NOT call interrupt() directly."""
        # Arrange
        from soni.compiler.nodes.collect import collect_node
        import soni.compiler.nodes.collect as collect_module

        config = MagicMock()
        config.slot = "amount"
        config.message = "Enter amount:"

        state = {"flow_slots": {}}
        runtime = MagicMock()

        # Act
        with pytest.raises(AttributeError):
            # If module uses interrupt, it should NOT be imported at module level
            _ = collect_module.interrupt


class TestConfirmNode:
    """Tests for confirm_node returning PendingTask."""

    @pytest.mark.asyncio
    async def test_confirm_returns_pending_task_when_unconfirmed(self):
        """Test that confirm_node returns ConfirmTask when not confirmed."""
        # Arrange
        from soni.compiler.nodes.confirm import confirm_node

        config = MagicMock()
        config.message = "Proceed with transfer?"

        state = {
            "flow_slots": {"amount": "500", "destination": "savings"},
            "_confirmed": False,
        }
        runtime = MagicMock()

        # Act
        result = await confirm_node(state, runtime, config)

        # Assert
        assert "_pending_task" in result
        task = result["_pending_task"]
        assert is_confirm(task)
        assert "Proceed" in task["prompt"] or task["prompt"] == config.message

    @pytest.mark.asyncio
    async def test_confirm_returns_empty_when_already_confirmed(self):
        """Test that confirm_node returns empty when already confirmed."""
        # Arrange
        from soni.compiler.nodes.confirm import confirm_node

        config = MagicMock()
        state = {"_confirmed": True}
        runtime = MagicMock()

        # Act
        result = await confirm_node(state, runtime, config)

        # Assert
        assert "_pending_task" not in result or result.get("_pending_task") is None


class TestActionNode:
    """Tests for action_node returning InformTask."""

    @pytest.mark.asyncio
    async def test_action_returns_inform_task_with_result(self):
        """Test that action_node returns InformTask with action result."""
        # Arrange
        from soni.compiler.nodes.action import action_node

        config = MagicMock()
        config.action_name = "check_balance"

        mock_action_result = MagicMock()
        mock_action_result.message = "Your balance is $1,234"

        state = {"flow_slots": {"account": "checking"}}
        runtime = MagicMock()
        runtime.context.action_registry.execute = AsyncMock(return_value=mock_action_result)

        # Act
        result = await action_node(state, runtime, config)

        # Assert
        assert "_pending_task" in result
        task = result["_pending_task"]
        assert is_inform(task)
        assert "balance" in task["prompt"].lower() or task["prompt"] == mock_action_result.message

    @pytest.mark.asyncio
    async def test_action_inform_does_not_wait_by_default(self):
        """Test that action result InformTask does not wait for ack by default."""
        # Arrange
        from soni.compiler.nodes.action import action_node

        config = MagicMock()
        mock_result = MagicMock()
        mock_result.message = "Done"

        state = {}
        runtime = MagicMock()
        runtime.context.action_registry.execute = AsyncMock(return_value=mock_result)

        # Act
        result = await action_node(state, runtime, config)

        # Assert
        task = result["_pending_task"]
        assert task.get("wait_for_ack") is not True
```

**Verify tests fail:**
```bash
uv run pytest tests/unit/compiler/test_subgraph_nodes.py -v
# Expected: FAILED (nodes not yet migrated)
```

**Commit:**
```bash
git add tests/
git commit -m "test(HIG-004): add failing tests for subgraph node migration"
```

---

### Green Phase: Make Tests Pass

#### Paso 1: Modificar collect_node

**Archivo:** `src/soni/compiler/nodes/collect.py`

```python
"""Collect node for gathering slot values from user."""
from typing import Any

from soni.core.pending_task import collect
from soni.core.interpolation import interpolate


async def collect_node(
    state: dict[str, Any],
    runtime: Any,
    config: Any,
) -> dict[str, Any]:
    """Collect a slot value from the user.

    Returns PendingTask instead of calling interrupt() directly.
    The orchestrator will handle the interrupt.
    """
    slot_name = config.slot
    slot_value = state.get("flow_slots", {}).get(slot_name)

    if not slot_value:
        # Slot is empty, need user input
        prompt = interpolate(config.message, state)
        return {
            "_pending_task": collect(
                prompt=prompt,
                slot=slot_name,
                options=getattr(config, "options", None),
                metadata={"expected_format": getattr(config, "format", None)},
            ),
        }

    # Slot has value, continue
    return {}
```

#### Paso 2: Modificar confirm_node

**Archivo:** `src/soni/compiler/nodes/confirm.py`

```python
"""Confirm node for user confirmation."""
from typing import Any

from soni.core.pending_task import confirm
from soni.core.interpolation import interpolate


async def confirm_node(
    state: dict[str, Any],
    runtime: Any,
    config: Any,
) -> dict[str, Any]:
    """Ask user for confirmation.

    Returns PendingTask instead of calling interrupt() directly.
    """
    if state.get("_confirmed"):
        # Already confirmed
        return {}

    prompt = interpolate(config.message, state)
    return {
        "_pending_task": confirm(
            prompt=prompt,
            options=getattr(config, "options", ["yes", "no"]),
        ),
    }
```

#### Paso 3: Modificar action_node

**Archivo:** `src/soni/compiler/nodes/action.py`

```python
"""Action node for executing business actions."""
from typing import Any

from soni.core.pending_task import inform


async def action_node(
    state: dict[str, Any],
    runtime: Any,
    config: Any,
) -> dict[str, Any]:
    """Execute an action and return result as InformTask.

    Returns PendingTask with action result for display.
    """
    action_registry = runtime.context.action_registry
    slots = state.get("flow_slots", {})

    result = await action_registry.execute(config.action_name, slots)

    return {
        "_pending_task": inform(
            prompt=result.message,
            wait_for_ack=getattr(config, "wait_for_ack", False),
            metadata={"action": config.action_name},
        ),
    }
```

**Verify tests pass:**
```bash
uv run pytest tests/unit/compiler/test_subgraph_nodes.py -v
```

**Commit:**
```bash
git add src/ tests/
git commit -m "feat(HIG-004): migrate subgraph nodes to use PendingTask factories"
```

---

## Limpieza Progresiva

**Código a eliminar en esta fase:**

| Archivo | Líneas/Código | Razón |
|---------|---------------|-------|
| `collect.py` | `from langgraph.types import interrupt` | Ya no se usa |
| `collect.py` | `interrupt({...})` call | Reemplazado por return |
| `confirm.py` | `from langgraph.types import interrupt` | Ya no se usa |
| `confirm.py` | `interrupt({...})` call | Reemplazado por return |
| Cualquier nodo | `_need_input` field | Ya no necesario |

**Eliminar imports obsoletos:**
```python
# ELIMINAR de todos los nodos de subgraph:
from langgraph.types import interrupt  # Ya no se usa aquí
```

---

## Criterios de Éxito

- [ ] `collect_node` retorna `CollectTask` (no llama a `interrupt()`)
- [ ] `confirm_node` retorna `ConfirmTask` (no llama a `interrupt()`)
- [ ] `action_node` retorna `InformTask` con resultado de acción
- [ ] Ningún nodo de subgraph importa ni usa `interrupt` directamente
- [ ] No existe `_need_input` en los returns de nodos
- [ ] Todos los tests pasan
- [ ] `uv run mypy src/soni/compiler/nodes/` sin errores

## Validación Manual

```bash
# Verificar que interrupt no se usa en subgraph nodes
grep -r "from langgraph.types import interrupt" src/soni/compiler/nodes/
# Expected: No results (or only in comments)

# Verificar que _need_input no se usa
grep -r "_need_input" src/soni/compiler/nodes/
# Expected: No results

# Ejecutar tests
uv run pytest tests/unit/compiler/test_subgraph_nodes.py -v

# Verificar tipos
uv run mypy src/soni/compiler/nodes/
```

## Referencias

- [ADR-002](../analysis/ADR-002-Human-Input-Gate-Architecture.md) - Sección 4: Modified Subgraphs
