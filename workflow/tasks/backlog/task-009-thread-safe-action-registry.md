## Task: 009 - Implement Thread-Safe ActionRegistry

**ID de tarea:** 009
**Hito:** 3 - Production Readiness
**Dependencias:** Ninguna
**Duración estimada:** 4 horas
**Prioridad:** MEDIA

### Objetivo

Hacer que `ActionRegistry` sea thread-safe para soportar registración concurrente de acciones en entornos multi-threaded, previniendo race conditions y garantizando consistencia.

### Contexto

El `ActionRegistry` actual usa un diccionario de clase compartido sin sincronización:

**Ubicación:** `src/soni/actions/registry.py:32-33`

```python
class ActionRegistry:
    """Registry for action handlers with global and local registration."""

    _global_actions: dict[str, ActionFunc] = {}  # Class variable - shared!

    def __init__(self) -> None:
        self._actions: dict[str, ActionFunc] = {}  # Instance variable
```

**Problemas potenciales:**
1. Múltiples threads registrando acciones simultáneamente pueden causar race conditions
2. No hay protección contra registración duplicada
3. En entornos como FastAPI con workers múltiples, el comportamiento puede ser impredecible

**Escenario de riesgo:**
```python
# Thread 1                          # Thread 2
ActionRegistry.register("action1")   ActionRegistry.register("action2")
# Ambos modifican _global_actions simultáneamente
```

### Entregables

- [ ] Agregar `threading.Lock` para proteger `_global_actions`
- [ ] Agregar logging cuando se registra una acción
- [ ] Agregar warning cuando se sobrescribe una acción existente
- [ ] Considerar `RLock` si se necesita re-entrancy
- [ ] Tests de concurrencia

### Implementación Detallada

#### Paso 1: Agregar lock para operaciones globales

**Archivo a modificar:** `src/soni/actions/registry.py`

**ANTES:**
```python
import logging
from typing import Any, Awaitable, Callable

logger = logging.getLogger(__name__)

ActionFunc = Callable[..., dict[str, Any] | Awaitable[dict[str, Any]]]


class ActionRegistry:
    """Registry for action handlers with global and local registration."""

    _global_actions: dict[str, ActionFunc] = {}

    def __init__(self) -> None:
        self._actions: dict[str, ActionFunc] = {}
```

**DESPUÉS:**
```python
import logging
import threading
from typing import Any, Awaitable, Callable

logger = logging.getLogger(__name__)

ActionFunc = Callable[..., dict[str, Any] | Awaitable[dict[str, Any]]]


class ActionRegistry:
    """Thread-safe registry for action handlers.

    Supports both global (class-level) and local (instance-level) registration.
    Global registration is thread-safe using a lock.

    Usage:
        # Global registration (decorator)
        @ActionRegistry.register("my_action")
        def my_action(slot: str) -> dict[str, Any]:
            return {"result": slot}

        # Local registration (instance method)
        registry = ActionRegistry()
        registry.register_local("custom_action", my_custom_func)
    """

    _global_actions: dict[str, ActionFunc] = {}
    _global_lock: threading.Lock = threading.Lock()

    def __init__(self) -> None:
        """Initialize a new ActionRegistry instance.

        Instance-level actions take precedence over global actions.
        """
        self._actions: dict[str, ActionFunc] = {}
        self._local_lock: threading.Lock = threading.Lock()
```

#### Paso 2: Proteger métodos de registro global

**Método `register` (decorator):**

```python
@classmethod
def register(cls, name: str) -> Callable[[ActionFunc], ActionFunc]:
    """Register a global action handler (thread-safe).

    Use as a decorator:
        @ActionRegistry.register("action_name")
        def my_action(...) -> dict[str, Any]:
            ...

    Args:
        name: Unique name for the action

    Returns:
        Decorator function
    """
    def decorator(func: ActionFunc) -> ActionFunc:
        with cls._global_lock:
            if name in cls._global_actions:
                logger.warning(
                    f"Overwriting existing global action '{name}'. "
                    f"Previous: {cls._global_actions[name].__name__}, "
                    f"New: {func.__name__}"
                )
            cls._global_actions[name] = func
            logger.debug(f"Registered global action: {name}")
        return func

    return decorator
```

**Método `get`:**

```python
def get(self, name: str) -> ActionFunc | None:
    """Get an action by name (thread-safe).

    Checks local actions first, then global actions.

    Args:
        name: Action name to look up

    Returns:
        Action function if found, None otherwise
    """
    # Local actions don't need global lock (instance-specific)
    with self._local_lock:
        if name in self._actions:
            return self._actions[name]

    # Global actions need lock for read safety
    with self._global_lock:
        return self._global_actions.get(name)
```

**Método `register_local`:**

```python
def register_local(self, name: str, func: ActionFunc) -> None:
    """Register an instance-local action handler (thread-safe).

    Local actions take precedence over global actions.

    Args:
        name: Unique name for the action
        func: Action function to register
    """
    with self._local_lock:
        if name in self._actions:
            logger.warning(
                f"Overwriting existing local action '{name}'. "
                f"Previous: {self._actions[name].__name__}, "
                f"New: {func.__name__}"
            )
        self._actions[name] = func
        logger.debug(f"Registered local action: {name}")
```

#### Paso 3: Proteger métodos de limpieza

**Método `clear_global`:**

```python
@classmethod
def clear_global(cls) -> None:
    """Clear all global actions (thread-safe).

    Warning: This affects all instances. Use with caution.
    """
    with cls._global_lock:
        count = len(cls._global_actions)
        cls._global_actions.clear()
        logger.info(f"Cleared {count} global actions")

# Backward compatibility alias
clear = clear_global
```

**Método `clear_local`:**

```python
def clear_local(self) -> None:
    """Clear instance-local actions (thread-safe)."""
    with self._local_lock:
        count = len(self._actions)
        self._actions.clear()
        logger.debug(f"Cleared {count} local actions")
```

#### Paso 4: Agregar método de introspección thread-safe

```python
def list_actions(self) -> dict[str, list[str]]:
    """List all available actions (thread-safe).

    Returns:
        Dictionary with 'global' and 'local' keys containing action names
    """
    with self._local_lock:
        local_names = list(self._actions.keys())

    with self._global_lock:
        global_names = list(self._global_actions.keys())

    return {
        "global": global_names,
        "local": local_names,
    }
```

### TDD Cycle (MANDATORY for new features)

#### Red Phase: Write Failing Tests

**Test file:** `tests/unit/actions/test_registry_thread_safety.py`

```python
import pytest
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

from soni.actions.registry import ActionRegistry


class TestActionRegistryThreadSafety:
    """Tests for thread-safe ActionRegistry operations."""

    @pytest.fixture(autouse=True)
    def cleanup(self):
        """Clear global registry before and after each test."""
        ActionRegistry.clear_global()
        yield
        ActionRegistry.clear_global()

    def test_concurrent_global_registration(self):
        """Test that concurrent global registrations don't corrupt state."""
        num_threads = 10
        actions_per_thread = 100

        def register_actions(thread_id: int) -> list[str]:
            registered = []
            for i in range(actions_per_thread):
                name = f"action_{thread_id}_{i}"

                @ActionRegistry.register(name)
                def action(**kwargs) -> dict:
                    return {"thread": thread_id, "index": i}

                registered.append(name)
            return registered

        # Run concurrent registrations
        with ThreadPoolExecutor(max_workers=num_threads) as executor:
            futures = [
                executor.submit(register_actions, i)
                for i in range(num_threads)
            ]
            all_registered = []
            for future in as_completed(futures):
                all_registered.extend(future.result())

        # Verify all actions were registered
        registry = ActionRegistry()
        for name in all_registered:
            assert registry.get(name) is not None, f"Action {name} not found"

        # Verify count
        expected_count = num_threads * actions_per_thread
        actions = registry.list_actions()
        assert len(actions["global"]) == expected_count

    def test_concurrent_local_registration(self):
        """Test that concurrent local registrations on same instance are safe."""
        registry = ActionRegistry()
        num_threads = 10
        actions_per_thread = 50

        def register_local_actions(thread_id: int) -> list[str]:
            registered = []
            for i in range(actions_per_thread):
                name = f"local_{thread_id}_{i}"

                def action(**kwargs) -> dict:
                    return {"thread": thread_id, "index": i}

                registry.register_local(name, action)
                registered.append(name)
            return registered

        with ThreadPoolExecutor(max_workers=num_threads) as executor:
            futures = [
                executor.submit(register_local_actions, i)
                for i in range(num_threads)
            ]
            all_registered = []
            for future in as_completed(futures):
                all_registered.extend(future.result())

        # Verify all actions
        for name in all_registered:
            assert registry.get(name) is not None, f"Local action {name} not found"

    def test_concurrent_read_write(self):
        """Test concurrent reads and writes don't deadlock or corrupt."""
        registry = ActionRegistry()
        stop_event = threading.Event()
        errors = []

        # Pre-register some actions
        for i in range(10):
            @ActionRegistry.register(f"preset_{i}")
            def preset_action(**kwargs) -> dict:
                return {"preset": i}

        def reader():
            """Continuously read actions."""
            while not stop_event.is_set():
                try:
                    for i in range(10):
                        _ = registry.get(f"preset_{i}")
                    _ = registry.list_actions()
                except Exception as e:
                    errors.append(f"Reader error: {e}")

        def writer(thread_id: int):
            """Continuously write new actions."""
            count = 0
            while not stop_event.is_set():
                try:
                    name = f"dynamic_{thread_id}_{count}"
                    registry.register_local(name, lambda **kwargs: {})
                    count += 1
                    time.sleep(0.001)
                except Exception as e:
                    errors.append(f"Writer {thread_id} error: {e}")

        # Start readers and writers
        threads = []
        for i in range(3):
            threads.append(threading.Thread(target=reader))
        for i in range(2):
            threads.append(threading.Thread(target=writer, args=(i,)))

        for t in threads:
            t.start()

        # Let them run
        time.sleep(0.5)
        stop_event.set()

        for t in threads:
            t.join(timeout=2)

        assert len(errors) == 0, f"Errors during concurrent access: {errors}"

    def test_duplicate_registration_logs_warning(self, caplog):
        """Test that overwriting an action logs a warning."""
        import logging

        with caplog.at_level(logging.WARNING):
            @ActionRegistry.register("duplicate_test")
            def first_action(**kwargs) -> dict:
                return {"first": True}

            @ActionRegistry.register("duplicate_test")
            def second_action(**kwargs) -> dict:
                return {"second": True}

        # Check warning was logged
        assert "Overwriting" in caplog.text
        assert "duplicate_test" in caplog.text

    def test_clear_global_is_atomic(self):
        """Test that clear_global is atomic and doesn't interfere with reads."""
        # Register actions
        for i in range(100):
            @ActionRegistry.register(f"clear_test_{i}")
            def action(**kwargs) -> dict:
                return {}

        registry = ActionRegistry()
        errors = []

        def reader():
            for _ in range(1000):
                try:
                    actions = registry.list_actions()
                    # Should either have 0 or 100 actions, never partial
                    count = len(actions["global"])
                    if count not in [0, 100] and "clear_test" in str(actions):
                        errors.append(f"Partial state detected: {count} actions")
                except Exception as e:
                    errors.append(f"Reader error: {e}")

        def clearer():
            time.sleep(0.01)
            ActionRegistry.clear_global()

        threads = [
            threading.Thread(target=reader),
            threading.Thread(target=clearer),
        ]

        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # Note: This test may not catch all race conditions, but it's a basic check
        # In practice, dict operations in CPython are atomic due to GIL
        assert len(errors) == 0, f"Errors: {errors}"
```

**Verify tests fail:**
```bash
uv run pytest tests/unit/actions/test_registry_thread_safety.py -v
# Expected: May pass due to GIL, but logging tests should fail
```

**Commit:**
```bash
git add tests/
git commit -m "test: add thread safety tests for ActionRegistry"
```

#### Green Phase: Make Tests Pass

See "Implementación Detallada" section.

**Verify tests pass:**
```bash
uv run pytest tests/unit/actions/test_registry_thread_safety.py -v
# Expected: PASSED
```

**Commit:**
```bash
git add src/ tests/
git commit -m "feat: make ActionRegistry thread-safe

- Add threading.Lock for global action registration
- Add threading.Lock for local action registration
- Log warnings on duplicate registration
- Add list_actions() for introspection
- Full test coverage for concurrent operations"
```

### Criterios de Éxito

- [ ] Todas las operaciones de registro son thread-safe
- [ ] Warnings se loguean al sobrescribir acciones
- [ ] No hay deadlocks en operaciones concurrentes
- [ ] Tests de concurrencia pasan
- [ ] Performance no degradada significativamente
- [ ] Todos los tests pasan
- [ ] Linting pasa sin errores

### Validación Manual

**Comandos para validar:**

```bash
# Ejecutar tests de thread safety
uv run pytest tests/unit/actions/test_registry_thread_safety.py -v

# Stress test con muchos threads
uv run python -c "
import threading
from soni.actions.registry import ActionRegistry

def register_many(tid):
    for i in range(100):
        @ActionRegistry.register(f't{tid}_a{i}')
        def a(**k): return {}

threads = [threading.Thread(target=register_many, args=(i,)) for i in range(10)]
for t in threads: t.start()
for t in threads: t.join()
print(f'Total: {len(ActionRegistry._global_actions)} actions')
"
# Esperado: 1000 actions sin errores
```

### Referencias

- `src/soni/actions/registry.py` - Archivo a modificar
- Python threading documentation
- Thread-safe singleton patterns

### Notas Adicionales

**Consideraciones de performance:**
- CPython GIL ya proporciona cierta protección para operaciones de dict
- Los locks agregan overhead mínimo para operaciones de registro (poco frecuentes)
- Las lecturas son más frecuentes; considerar `RLock` o `ReadWriteLock` si es bottleneck

**Alternativas consideradas:**
- `threading.RLock` - Si se necesita re-entrancy (decorators anidados)
- `concurrent.futures.Lock` - No ofrece ventajas aquí
- Lock-free structures - Overkill para este caso de uso
