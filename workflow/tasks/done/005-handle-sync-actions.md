## Task: 005 - Handle Sync Actions in ActionHandler

**ID de tarea:** 005
**Hito:** Async-First Compliance
**Dependencias:** Ninguna
**Duración estimada:** 1.5 horas

### Objetivo

Garantizar que acciones síncronas no bloqueen el event loop ejecutándolas en `asyncio.to_thread()` o logueando warning de deprecación.

### Contexto

Actualmente `ActionHandler.execute()` permite acciones sync:

```python
if inspect.iscoroutinefunction(action):
    return await action(**filtered_inputs)
else:
    return action(**filtered_inputs)  # ¡BLOQUEA EVENT LOOP!
```

Esto viola el principio async-first y puede causar problemas de performance.

### Entregables

- [ ] Ejecutar acciones sync en `asyncio.to_thread()`
- [ ] Añadir logging warning para acciones sync (deprecation)
- [ ] Tests unitarios para ambos paths

### Implementación Detallada

#### Paso 1: Actualizar execute()

**Archivo(s) a modificar:** `src/soni/actions/handler.py`

```python
import asyncio

async def execute(self, action_name: str, inputs: dict[str, Any]) -> dict[str, Any]:
    # ... validation unchanged ...

    try:
        if inspect.iscoroutinefunction(action):
            return await cast(Awaitable[dict[str, Any]], action(**filtered_inputs))
        else:
            # Sync actions: warn and run in thread pool
            logger.warning(
                f"Action '{action_name}' is synchronous. "
                "Consider converting to async for better performance."
            )
            return await asyncio.to_thread(action, **filtered_inputs)
    except Exception as e:
        raise ActionError(f"Action execution failed: {e}") from e
```

### TDD Cycle (MANDATORY)

#### Red Phase: Write Failing Tests

**Test file:** `tests/unit/actions/test_handler_sync_actions.py`

```python
import pytest
import asyncio
from unittest.mock import MagicMock

from soni.actions.handler import ActionHandler
from soni.actions.registry import ActionRegistry


@pytest.fixture
def registry_with_sync_action():
    """Create registry with a sync action."""
    registry = ActionRegistry()

    def sync_action(value: str) -> dict:
        return {"result": value}

    registry._actions["sync_test"] = sync_action
    return registry


@pytest.fixture
def registry_with_async_action():
    """Create registry with an async action."""
    registry = ActionRegistry()

    async def async_action(value: str) -> dict:
        return {"result": value}

    registry._actions["async_test"] = async_action
    return registry


class TestActionHandlerSyncActions:
    """Tests for sync action handling."""

    @pytest.mark.asyncio
    async def test_sync_action_runs_in_thread(self, registry_with_sync_action):
        """Test that sync actions are executed via to_thread."""
        # Arrange
        handler = ActionHandler(registry_with_sync_action)

        # Act
        result = await handler.execute("sync_test", {"value": "hello"})

        # Assert
        assert result == {"result": "hello"}

    @pytest.mark.asyncio
    async def test_sync_action_logs_warning(self, registry_with_sync_action, caplog):
        """Test that sync actions trigger deprecation warning."""
        # Arrange
        import logging
        caplog.set_level(logging.WARNING)
        handler = ActionHandler(registry_with_sync_action)

        # Act
        await handler.execute("sync_test", {"value": "hello"})

        # Assert
        assert "synchronous" in caplog.text.lower()
        assert "sync_test" in caplog.text

    @pytest.mark.asyncio
    async def test_async_action_no_warning(self, registry_with_async_action, caplog):
        """Test that async actions don't trigger warning."""
        # Arrange
        import logging
        caplog.set_level(logging.WARNING)
        handler = ActionHandler(registry_with_async_action)

        # Act
        await handler.execute("async_test", {"value": "hello"})

        # Assert
        assert "synchronous" not in caplog.text.lower()
```

**Verify tests fail:**
```bash
uv run pytest tests/unit/actions/test_handler_sync_actions.py -v
# Expected: FAILED (no to_thread, no warning)
```

#### Green Phase: Make Tests Pass

Implementar cambios en `ActionHandler`.

```bash
uv run pytest tests/unit/actions/test_handler_sync_actions.py -v
# Expected: PASSED ✅
```

### Criterios de Éxito

- [ ] Acciones sync no bloquean event loop
- [ ] Warning se loguea para acciones sync
- [ ] Acciones async funcionan sin warning
- [ ] `uv run pytest` pasa
- [ ] `uv run ruff check .` sin errores
- [ ] `uv run mypy src/soni` sin errores

### Validación Manual

```bash
uv run pytest tests/unit/actions/ -v
uv run ruff check src/soni/actions/
uv run mypy src/soni/actions/
```

### Referencias

- `src/soni/actions/handler.py:57-66` - Código actual
