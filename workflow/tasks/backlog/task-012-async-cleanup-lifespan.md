## Task: 012 - Implement Async Cleanup in FastAPI Lifespan

**ID de tarea:** 012
**Hito:** 3 - Production Readiness
**Dependencias:** Ninguna
**Duración estimada:** 2 horas
**Prioridad:** BAJA

### Objetivo

Implementar cleanup async apropiado en el lifespan de FastAPI para liberar recursos correctamente cuando el servidor se detiene, previniendo resource leaks.

### Contexto

El lifespan actual no implementa cleanup async:

**Ubicación:** `src/soni/server/api.py:31-67`

```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    # ... initialization ...
    yield

    # Cleanup - actualmente solo resetea a None
    logger.info("Soni server shutting down")
    if hasattr(app.state, "runtime"):
        app.state.runtime = None  # No await cleanup!
    if hasattr(app.state, "config"):
        app.state.config = None
```

**Problemas potenciales:**
1. RuntimeLoop puede tener recursos async (checkpointer connections)
2. DSPy puede tener connections abiertas
3. No hay graceful shutdown de conversaciones activas
4. Posibles resource leaks en producción

### Entregables

- [ ] Agregar método `cleanup()` a RuntimeLoop
- [ ] Actualizar lifespan para llamar cleanup async
- [ ] Cerrar checkpointer connections apropiadamente
- [ ] Logging de cleanup para debugging
- [ ] Tests de cleanup

### Implementación Detallada

#### Paso 1: Agregar método cleanup a RuntimeLoop

**Archivo a modificar:** `src/soni/runtime/loop.py`

```python
async def cleanup(self) -> None:
    """Clean up runtime resources.

    Should be called during server shutdown to release resources gracefully.
    """
    logger.info("RuntimeLoop cleanup starting...")

    if not self._components:
        logger.debug("No components to clean up")
        return

    # Close checkpointer if it has a close method
    checkpointer = self._components.checkpointer
    if checkpointer:
        if hasattr(checkpointer, "aclose"):
            try:
                await checkpointer.aclose()
                logger.debug("Checkpointer closed (async)")
            except Exception as e:
                logger.warning(f"Error closing checkpointer: {e}")
        elif hasattr(checkpointer, "close"):
            try:
                checkpointer.close()
                logger.debug("Checkpointer closed (sync)")
            except Exception as e:
                logger.warning(f"Error closing checkpointer: {e}")

    # Clear references
    self._components = None
    self._graph = None

    logger.info("RuntimeLoop cleanup completed")
```

#### Paso 2: Actualizar lifespan context manager

**Archivo a modificar:** `src/soni/server/api.py`

**ANTES:**
```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan - initialize on startup, cleanup on shutdown."""
    # ... initialization code ...

    yield

    # Cleanup
    logger.info("Soni server shutting down")
    if hasattr(app.state, "runtime"):
        app.state.runtime = None
    if hasattr(app.state, "config"):
        app.state.config = None
```

**DESPUÉS:**
```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan - initialize on startup, cleanup on shutdown.

    Handles graceful initialization and cleanup of server resources.
    """
    # === STARTUP ===
    config_path = Path(os.getenv("SONI_CONFIG_PATH", "soni.yaml"))

    if config_path.exists():
        logger.info(f"Loading configuration from {config_path}")
        try:
            loader = ConfigLoader()
            config = loader.from_yaml(config_path)
            runtime = RuntimeLoop(config)
            await runtime.initialize()

            app.state.config = config
            app.state.runtime = runtime

            logger.info("Soni server initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize server: {e}")
            raise
    else:
        logger.warning(
            f"Configuration file {config_path} not found. "
            "Server starting without configuration - "
            "use POST /config to load configuration."
        )
        app.state.config = None
        app.state.runtime = None

    yield

    # === SHUTDOWN ===
    logger.info("Soni server shutting down...")

    # Cleanup runtime (releases async resources)
    runtime = getattr(app.state, "runtime", None)
    if runtime is not None:
        try:
            await runtime.cleanup()
            logger.info("Runtime cleanup completed")
        except Exception as e:
            logger.error(f"Error during runtime cleanup: {e}")

    # Clear references
    app.state.runtime = None
    app.state.config = None

    logger.info("Soni server shutdown completed")
```

#### Paso 3: Agregar cleanup al checkpointer

**Archivo a verificar/modificar:** `src/soni/runtime/checkpointer.py`

Verificar si los checkpointers tienen métodos de cleanup:

```python
# Para SQLite checkpointer
class SQLiteCheckpointer:
    async def aclose(self) -> None:
        """Close database connection."""
        if self._conn:
            self._conn.close()
            self._conn = None

# Para Postgres checkpointer
class PostgresCheckpointer:
    async def aclose(self) -> None:
        """Close database connection pool."""
        if self._pool:
            await self._pool.close()
            self._pool = None
```

Si se usa LangGraph's built-in checkpointers, verificar su API de cleanup.

#### Paso 4: Agregar graceful shutdown para requests activas

**Archivo a modificar:** `src/soni/server/api.py`

Opcional: Agregar tracking de requests activas para graceful shutdown:

```python
from contextlib import asynccontextmanager
import asyncio

# Track active requests
_active_requests: set[str] = set()
_shutdown_event = asyncio.Event()


async def wait_for_active_requests(timeout: float = 30.0) -> None:
    """Wait for active requests to complete before shutdown.

    Args:
        timeout: Maximum time to wait in seconds
    """
    if not _active_requests:
        return

    logger.info(f"Waiting for {len(_active_requests)} active requests to complete...")

    try:
        # Wait with timeout
        start = asyncio.get_event_loop().time()
        while _active_requests and (asyncio.get_event_loop().time() - start) < timeout:
            await asyncio.sleep(0.1)

        if _active_requests:
            logger.warning(
                f"Shutdown timeout reached with {len(_active_requests)} requests still active"
            )
    except Exception as e:
        logger.error(f"Error waiting for active requests: {e}")


# En el endpoint /message, usar context manager para tracking:
@app.post("/message", response_model=MessageResponse)
async def process_message(
    request: MessageRequest,
    runtime: RuntimeDep,
) -> MessageResponse:
    request_id = f"{request.user_id}-{id(request)}"
    _active_requests.add(request_id)
    try:
        # ... existing code ...
    finally:
        _active_requests.discard(request_id)
```

### TDD Cycle (MANDATORY for new features)

#### Red Phase: Write Failing Tests

**Test file:** `tests/unit/runtime/test_cleanup.py`

```python
import pytest
from unittest.mock import AsyncMock, MagicMock, patch


class TestRuntimeLoopCleanup:
    """Tests for RuntimeLoop cleanup functionality."""

    @pytest.fixture
    def mock_config(self):
        config = MagicMock()
        config.settings.persistence.backend = "memory"
        return config

    @pytest.mark.asyncio
    async def test_cleanup_closes_checkpointer(self, mock_config):
        """Test that cleanup closes the checkpointer."""
        from soni.runtime.loop import RuntimeLoop

        runtime = RuntimeLoop(config=mock_config)
        await runtime.initialize()

        # Mock checkpointer with aclose
        mock_checkpointer = MagicMock()
        mock_checkpointer.aclose = AsyncMock()
        runtime._components.checkpointer = mock_checkpointer

        await runtime.cleanup()

        mock_checkpointer.aclose.assert_called_once()

    @pytest.mark.asyncio
    async def test_cleanup_handles_sync_close(self, mock_config):
        """Test that cleanup handles sync close method."""
        from soni.runtime.loop import RuntimeLoop

        runtime = RuntimeLoop(config=mock_config)
        await runtime.initialize()

        # Mock checkpointer with only sync close
        mock_checkpointer = MagicMock(spec=["close"])
        mock_checkpointer.close = MagicMock()
        runtime._components.checkpointer = mock_checkpointer

        await runtime.cleanup()

        mock_checkpointer.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_cleanup_handles_no_checkpointer(self, mock_config):
        """Test that cleanup handles missing checkpointer gracefully."""
        from soni.runtime.loop import RuntimeLoop

        runtime = RuntimeLoop(config=mock_config)
        await runtime.initialize()

        # Remove checkpointer
        runtime._components.checkpointer = None

        # Should not raise
        await runtime.cleanup()

    @pytest.mark.asyncio
    async def test_cleanup_clears_components(self, mock_config):
        """Test that cleanup clears component references."""
        from soni.runtime.loop import RuntimeLoop

        runtime = RuntimeLoop(config=mock_config)
        await runtime.initialize()

        assert runtime._components is not None

        await runtime.cleanup()

        assert runtime._components is None

    @pytest.mark.asyncio
    async def test_cleanup_before_init_is_safe(self, mock_config):
        """Test that cleanup before initialization doesn't fail."""
        from soni.runtime.loop import RuntimeLoop

        runtime = RuntimeLoop(config=mock_config)
        # Don't initialize

        # Should not raise
        await runtime.cleanup()

    @pytest.mark.asyncio
    async def test_cleanup_handles_checkpointer_error(self, mock_config, caplog):
        """Test that cleanup handles checkpointer close errors gracefully."""
        import logging
        from soni.runtime.loop import RuntimeLoop

        runtime = RuntimeLoop(config=mock_config)
        await runtime.initialize()

        # Mock checkpointer that raises on close
        mock_checkpointer = MagicMock()
        mock_checkpointer.aclose = AsyncMock(side_effect=Exception("Close failed"))
        runtime._components.checkpointer = mock_checkpointer

        with caplog.at_level(logging.WARNING):
            await runtime.cleanup()  # Should not raise

        assert "Error closing checkpointer" in caplog.text


class TestLifespanCleanup:
    """Tests for FastAPI lifespan cleanup."""

    @pytest.mark.asyncio
    async def test_lifespan_calls_runtime_cleanup(self):
        """Test that lifespan calls runtime.cleanup() on shutdown."""
        from soni.server.api import lifespan, app
        from unittest.mock import AsyncMock

        mock_runtime = MagicMock()
        mock_runtime.cleanup = AsyncMock()

        # Simulate lifespan
        app.state.runtime = mock_runtime
        app.state.config = MagicMock()

        async with lifespan(app):
            pass  # Yield point

        mock_runtime.cleanup.assert_called_once()
```

**Verify tests fail:**
```bash
uv run pytest tests/unit/runtime/test_cleanup.py -v
# Expected: FAILED (cleanup method doesn't exist)
```

**Commit:**
```bash
git add tests/
git commit -m "test: add failing tests for async cleanup"
```

#### Green Phase: Make Tests Pass

See "Implementación Detallada" section.

**Verify tests pass:**
```bash
uv run pytest tests/unit/runtime/test_cleanup.py -v
# Expected: PASSED
```

**Commit:**
```bash
git add src/ tests/
git commit -m "feat: implement async cleanup in FastAPI lifespan

- Add RuntimeLoop.cleanup() method
- Close checkpointer connections on shutdown
- Handle both async and sync close methods
- Graceful error handling during cleanup
- Clear component references"
```

### Criterios de Éxito

- [ ] `RuntimeLoop.cleanup()` implementado
- [ ] Lifespan llama cleanup async
- [ ] Checkpointer connections se cierran
- [ ] Errores de cleanup no crashean el shutdown
- [ ] Logging apropiado durante cleanup
- [ ] Todos los tests pasan

### Validación Manual

**Comandos para validar:**

```bash
# Iniciar servidor
uv run soni server --config examples/banking/soni.yaml &
PID=$!

# Hacer algunas requests
curl -X POST http://localhost:8000/message \
  -H "Content-Type: application/json" \
  -d '{"user_id": "test", "message": "hello"}'

# Enviar SIGTERM y verificar logs de cleanup
kill $PID

# Logs deberían mostrar:
# "Soni server shutting down..."
# "RuntimeLoop cleanup starting..."
# "Checkpointer closed..."
# "RuntimeLoop cleanup completed"
# "Soni server shutdown completed"
```

### Referencias

- FastAPI Lifespan documentation
- Python asyncio cleanup patterns
- LangGraph checkpointer API

### Notas Adicionales

**Consideraciones de producción:**
- Considerar timeout para cleanup (no bloquear shutdown indefinidamente)
- Health endpoint debería indicar "shutting_down" durante cleanup
- Kubernetes/Docker necesitan SIGTERM handling apropiado

**Recursos que pueden necesitar cleanup:**
- Database connections (checkpointer)
- HTTP clients (si se usan para actions)
- Cache connections (if implemented)
- Background tasks
