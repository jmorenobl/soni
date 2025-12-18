## Task: TASK-002 - Server API: Eliminar Estado Global Mutable

**ID de tarea:** 002
**Hito:** Security Hardening
**Dependencias:** Ninguna
**Duración estimada:** 3 horas
**Prioridad:** CRÍTICA

### Objetivo

Reemplazar las variables globales mutables `_runtime` y `_config` con el sistema de dependency injection de FastAPI, eliminando race conditions en deployments multi-worker.

### Contexto

El análisis identificó estado global mutable en `api.py:27-29`:

```python
_runtime: RuntimeLoop | None = None
_config: SoniConfig | None = None
```

**Problemas:**
1. **Race conditions:** En Uvicorn con múltiples workers, cada worker tiene su propia copia
2. **Testing difícil:** Requiere monkeypatching de módulos
3. **Violación DIP:** Componentes dependen de estado global, no de abstracciones
4. **Lifecycle confuso:** Variables modificadas en lifespan manager

**Solución:** Usar `app.state` de FastAPI + dependency injection pattern.

### Entregables

- [ ] Migrar `_runtime` y `_config` a `app.state`
- [ ] Crear dependency functions usando `Depends()`
- [ ] Eliminar variables globales del módulo
- [ ] Actualizar todos los endpoints para usar dependencies
- [ ] Agregar tests verificando DI correcto

### Implementación Detallada

#### Paso 1: Crear módulo de dependencies

**Archivo a crear:** `src/soni/server/dependencies.py`

```python
"""FastAPI dependencies for server endpoints."""

from __future__ import annotations

from typing import TYPE_CHECKING, Annotated

from fastapi import Depends, HTTPException, Request

if TYPE_CHECKING:
    from soni.config import SoniConfig
    from soni.runtime import RuntimeLoop


def get_app_state(request: Request) -> dict:
    """Get application state from request."""
    return request.app.state._state


def get_runtime(request: Request) -> "RuntimeLoop":
    """Dependency to get initialized RuntimeLoop.

    Raises:
        HTTPException: 503 if runtime not initialized
    """
    state = request.app.state
    runtime = getattr(state, "runtime", None)

    if runtime is None:
        raise HTTPException(
            status_code=503,
            detail={
                "error": "Service temporarily unavailable",
                "message": "Server is starting up. Please try again in a few seconds.",
            },
        )

    return runtime


def get_config(request: Request) -> "SoniConfig":
    """Dependency to get loaded configuration.

    Raises:
        HTTPException: 503 if config not loaded
    """
    state = request.app.state
    config = getattr(state, "config", None)

    if config is None:
        raise HTTPException(
            status_code=503,
            detail={
                "error": "Service not configured",
                "message": "Server configuration not loaded.",
            },
        )

    return config


# Type aliases for cleaner endpoint signatures
RuntimeDep = Annotated["RuntimeLoop", Depends(get_runtime)]
ConfigDep = Annotated["SoniConfig", Depends(get_config)]
```

**Explicación:**
- `get_runtime()` y `get_config()` acceden a `request.app.state`
- `RuntimeDep` y `ConfigDep` son type aliases para uso en endpoints
- Errores 503 apropiados cuando servicio no está listo

#### Paso 2: Actualizar lifespan manager

**Archivo a modificar:** `src/soni/server/api.py`

**Cambiar lifespan de:**
```python
@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    global _runtime, _config

    config_path = Path("soni.yaml")
    # ...
    _config = loader.from_yaml(config_path)
    _runtime = RuntimeLoop(config=_config)
    await _runtime.initialize()

    yield

    _runtime = None
    _config = None
```

**A:**
```python
@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan - initializes runtime on startup, cleans up on shutdown."""
    import os
    from pathlib import Path

    from soni.config import ConfigLoader
    from soni.runtime import RuntimeLoop

    # Get config path from environment or default
    config_path = Path(os.getenv("SONI_CONFIG_PATH", "soni.yaml"))

    logger.info(f"Loading configuration from {config_path}")

    try:
        loader = ConfigLoader()
        config = loader.from_yaml(config_path)
    except Exception as e:
        logger.error(f"Failed to load configuration: {e}")
        raise

    logger.info("Initializing RuntimeLoop...")
    runtime = RuntimeLoop(config=config)
    await runtime.initialize()

    # Store in app.state instead of globals
    app.state.config = config
    app.state.runtime = runtime

    logger.info("Server ready to accept requests")

    yield

    # Cleanup
    logger.info("Shutting down server...")
    app.state.runtime = None
    app.state.config = None
```

**Explicación:**
- Usa `app.state` en lugar de variables globales
- Lee `SONI_CONFIG_PATH` del environment (compatible con CLI)
- Mejor logging durante startup/shutdown

#### Paso 3: Eliminar variables globales

**Archivo a modificar:** `src/soni/server/api.py`

**Eliminar líneas 27-29:**
```python
# DELETE THESE LINES
_runtime: RuntimeLoop | None = None
_config: SoniConfig | None = None
```

**Eliminar función `get_runtime()` antigua (líneas 32-38):**
```python
# DELETE THIS FUNCTION
def get_runtime() -> RuntimeLoop:
    if _runtime is None:
        raise HTTPException(status_code=503, ...)
    return _runtime
```

#### Paso 4: Actualizar endpoints para usar dependencies

**Archivo a modificar:** `src/soni/server/api.py`

**Agregar import:**
```python
from soni.server.dependencies import RuntimeDep, ConfigDep, get_runtime
```

**Actualizar endpoint `/message`:**
```python
@app.post("/message", response_model=MessageResponse)
async def send_message(
    request: MessageRequest,
    runtime: RuntimeDep,  # Injected via Depends
) -> MessageResponse:
    """Process a user message and return bot response."""
    try:
        response = await runtime.process_message(
            message=request.message,
            user_id=request.user_id,
        )
        # ... rest of implementation
```

**Actualizar endpoint `/state/{user_id}`:**
```python
@app.get("/state/{user_id}", response_model=StateResponse)
async def get_state(
    user_id: str,
    runtime: RuntimeDep,  # Injected
) -> StateResponse:
    """Get current conversation state for a user."""
    state = await runtime.get_state(user_id)
    # ... rest of implementation
```

**Actualizar endpoint `/health`:**
```python
@app.get("/health", response_model=HealthResponse)
async def health_check(request: Request) -> HealthResponse:
    """Health check endpoint."""
    runtime = getattr(request.app.state, "runtime", None)

    return HealthResponse(
        status="healthy" if runtime is not None else "starting",
        version="0.8.0",
        initialized=runtime is not None,
    )
```

**Actualizar endpoint `/reset/{user_id}`:**
```python
@app.post("/reset/{user_id}", response_model=ResetResponse)
async def reset_conversation(
    user_id: str,
    runtime: RuntimeDep,  # Now can actually use runtime
) -> ResetResponse:
    """Reset conversation state for a user."""
    # TODO: Implement actual reset using runtime
    return ResetResponse(
        success=True,
        message=f"Conversation state for user '{user_id}' will be reset.",
    )
```

### TDD Cycle (MANDATORY)

#### Red Phase: Write Failing Tests

**Test file:** `tests/unit/server/test_dependencies.py`

```python
"""Tests for FastAPI dependency injection."""

import pytest
from unittest.mock import Mock, AsyncMock
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient

from soni.server.dependencies import get_runtime, get_config, RuntimeDep


class TestGetRuntime:
    """Test runtime dependency."""

    def test_returns_runtime_when_initialized(self):
        """Should return runtime from app.state."""
        # Arrange
        mock_runtime = Mock()
        mock_request = Mock(spec=Request)
        mock_request.app.state.runtime = mock_runtime

        # Act
        result = get_runtime(mock_request)

        # Assert
        assert result is mock_runtime

    def test_raises_503_when_not_initialized(self):
        """Should raise 503 when runtime is None."""
        from fastapi import HTTPException

        mock_request = Mock(spec=Request)
        mock_request.app.state.runtime = None

        with pytest.raises(HTTPException) as exc_info:
            get_runtime(mock_request)

        assert exc_info.value.status_code == 503

    def test_raises_503_when_state_missing(self):
        """Should raise 503 when state attribute missing."""
        from fastapi import HTTPException

        mock_request = Mock(spec=Request)
        # Simulate missing attribute
        del mock_request.app.state.runtime

        with pytest.raises(HTTPException) as exc_info:
            get_runtime(mock_request)

        assert exc_info.value.status_code == 503


class TestGetConfig:
    """Test config dependency."""

    def test_returns_config_when_loaded(self):
        """Should return config from app.state."""
        mock_config = Mock()
        mock_request = Mock(spec=Request)
        mock_request.app.state.config = mock_config

        result = get_config(mock_request)

        assert result is mock_config

    def test_raises_503_when_not_loaded(self):
        """Should raise 503 when config is None."""
        from fastapi import HTTPException

        mock_request = Mock(spec=Request)
        mock_request.app.state.config = None

        with pytest.raises(HTTPException) as exc_info:
            get_config(mock_request)

        assert exc_info.value.status_code == 503


class TestDependencyIntegration:
    """Integration tests for dependency injection in endpoints."""

    @pytest.fixture
    def app_with_runtime(self):
        """Create app with mocked runtime in state."""
        from soni.server.api import create_app

        app = create_app()

        # Mock runtime in state
        mock_runtime = AsyncMock()
        mock_runtime.process_message = AsyncMock(return_value="Hello!")
        mock_runtime.get_state = AsyncMock(return_value=None)

        app.state.runtime = mock_runtime
        app.state.config = Mock()

        return app, mock_runtime

    def test_message_endpoint_uses_injected_runtime(self, app_with_runtime):
        """POST /message should use runtime from dependency."""
        app, mock_runtime = app_with_runtime
        client = TestClient(app)

        response = client.post(
            "/message",
            json={"user_id": "test", "message": "hello"},
        )

        # Verify runtime was called
        mock_runtime.process_message.assert_called_once()

    def test_state_endpoint_uses_injected_runtime(self, app_with_runtime):
        """GET /state should use runtime from dependency."""
        app, mock_runtime = app_with_runtime
        client = TestClient(app)

        response = client.get("/state/test-user")

        # Verify runtime.get_state was called
        mock_runtime.get_state.assert_called_once_with("test-user")

    def test_health_returns_starting_when_no_runtime(self):
        """Health should show starting when runtime not initialized."""
        from soni.server.api import create_app

        app = create_app()
        # Don't set runtime
        client = TestClient(app)

        response = client.get("/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "starting"
        assert data["initialized"] is False
```

**Verify tests fail:**
```bash
uv run pytest tests/unit/server/test_dependencies.py -v
# Expected: FAILED (dependencies module not created yet)
```

#### Green Phase: Make Tests Pass

Implement as described in Steps 1-4.

```bash
uv run pytest tests/unit/server/test_dependencies.py -v
# Expected: PASSED
```

### Criterios de Éxito

- [ ] No hay variables globales `_runtime` o `_config` en api.py
- [ ] Todos los endpoints usan `Depends()` para obtener runtime
- [ ] app.state contiene runtime y config
- [ ] Tests de dependency injection pasan
- [ ] Server funciona correctamente con `uv run soni server`
- [ ] Health endpoint muestra estado correcto

### Validación Manual

```bash
# Start server
SONI_CONFIG_PATH=examples/banking/soni.yaml uv run soni server

# Verify health shows initialized
curl http://localhost:8000/health
# Expected: {"status": "healthy", "initialized": true, ...}

# Test message endpoint
curl -X POST http://localhost:8000/message \
  -H "Content-Type: application/json" \
  -d '{"user_id": "test", "message": "hello"}'

# Start server without config (should fail gracefully)
uv run soni server --config nonexistent.yaml
# Expected: Startup failure with clear error
```

### Referencias

- FastAPI Dependencies: https://fastapi.tiangolo.com/tutorial/dependencies/
- FastAPI Application State: https://fastapi.tiangolo.com/advanced/events/
- Análisis original: Server API global state issues

### Notas Adicionales

- En producción con múltiples workers, cada worker tendrá su propia instancia de RuntimeLoop
- Para compartir estado entre workers, considerar Redis o similar (fuera de scope de esta tarea)
- `app.state` es thread-safe dentro de un worker
- Dependency injection mejora significativamente testability
