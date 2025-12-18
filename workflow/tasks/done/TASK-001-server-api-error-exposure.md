## Task: TASK-001 - Server API: Eliminar Exposición de Errores Sensibles

**ID de tarea:** 001
**Hito:** Security Hardening
**Dependencias:** Ninguna
**Duración estimada:** 2 horas
**Prioridad:** CRÍTICA

### Objetivo

Eliminar la exposición de mensajes de error internos a clientes HTTP, previniendo filtración de información sensible como rutas de archivos, stack traces, y configuración interna.

### Contexto

El análisis de seguridad identificó que `api.py:131` expone mensajes de error completos a clientes:

```python
raise HTTPException(status_code=500, detail=f"Error processing message: {str(e)}")
```

**Riesgos identificados:**
- Stack traces pueden revelar rutas de archivos del servidor
- Mensajes de error pueden contener URLs internas o connection strings
- Nombres de modelos/configuraciones pueden exponerse
- Facilita reconnaissance para ataques

**Referencias:**
- OWASP: Information Exposure Through Error Messages
- Análisis crítico: `server/api.py` líneas 129-131

### Entregables

- [ ] Crear sistema centralizado de manejo de errores HTTP
- [ ] Reemplazar exposición directa de `str(e)` por mensajes genéricos
- [ ] Agregar logging detallado server-side para debugging
- [ ] Mapear excepciones del framework a códigos HTTP apropiados
- [ ] Tests de seguridad verificando no-exposición

### Implementación Detallada

#### Paso 1: Crear módulo de error handling

**Archivo a crear:** `src/soni/server/errors.py`

```python
"""Server error handling - sanitizes errors for client responses."""

from __future__ import annotations

import logging
import uuid
from typing import TYPE_CHECKING

from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse

if TYPE_CHECKING:
    from soni.core.errors import SoniError

logger = logging.getLogger(__name__)


# Error messages safe to expose to clients
SAFE_ERROR_MESSAGES = {
    "ConfigError": "Configuration error. Please contact support.",
    "ValidationError": "Invalid request data.",
    "FlowError": "Flow execution error. Please try again.",
    "ActionError": "Action execution failed.",
    "NLUError": "Unable to understand request. Please rephrase.",
    "StateError": "Session state error. Please start a new conversation.",
    "GraphBuildError": "Internal configuration error.",
    "SlotError": "Invalid slot value provided.",
}

DEFAULT_ERROR_MESSAGE = "An internal error occurred. Please try again later."


def create_error_reference() -> str:
    """Generate unique error reference for client/server correlation."""
    return f"ERR-{uuid.uuid4().hex[:8].upper()}"


def get_safe_error_message(exception: Exception) -> str:
    """Get client-safe error message for exception type."""
    exception_type = type(exception).__name__
    return SAFE_ERROR_MESSAGES.get(exception_type, DEFAULT_ERROR_MESSAGE)


def get_http_status_for_exception(exception: Exception) -> int:
    """Map exception types to appropriate HTTP status codes."""
    from soni.core.errors import (
        ConfigError,
        ValidationError,
        SlotError,
        NLUError,
        FlowError,
        ActionError,
        StateError,
        GraphBuildError,
    )

    # Client errors (4xx)
    if isinstance(exception, ValidationError):
        return 400
    if isinstance(exception, SlotError):
        return 422
    if isinstance(exception, NLUError):
        return 422

    # Server errors (5xx)
    if isinstance(exception, ConfigError):
        return 500
    if isinstance(exception, GraphBuildError):
        return 500
    if isinstance(exception, (FlowError, ActionError, StateError)):
        return 500

    # Default to 500 for unknown errors
    return 500


def log_error_with_context(
    error_ref: str,
    exception: Exception,
    user_id: str | None = None,
    endpoint: str | None = None,
) -> None:
    """Log full error details server-side for debugging."""
    logger.error(
        f"[{error_ref}] Error in {endpoint or 'unknown'} "
        f"for user {user_id or 'unknown'}: {type(exception).__name__}: {exception}",
        exc_info=True,
        extra={
            "error_reference": error_ref,
            "user_id": user_id,
            "endpoint": endpoint,
            "exception_type": type(exception).__name__,
        },
    )


def create_error_response(
    exception: Exception,
    user_id: str | None = None,
    endpoint: str | None = None,
) -> HTTPException:
    """Create sanitized HTTPException for client response."""
    error_ref = create_error_reference()

    # Log full details server-side
    log_error_with_context(error_ref, exception, user_id, endpoint)

    # Return sanitized response to client
    status_code = get_http_status_for_exception(exception)
    safe_message = get_safe_error_message(exception)

    return HTTPException(
        status_code=status_code,
        detail={
            "error": safe_message,
            "reference": error_ref,
            "message": "If this problem persists, contact support with the reference code.",
        },
    )


async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Global exception handler for uncaught exceptions."""
    error_ref = create_error_reference()

    # Extract user_id if available
    user_id = None
    try:
        body = await request.json()
        user_id = body.get("user_id")
    except Exception:
        pass

    log_error_with_context(error_ref, exc, user_id, request.url.path)

    return JSONResponse(
        status_code=500,
        content={
            "error": DEFAULT_ERROR_MESSAGE,
            "reference": error_ref,
            "message": "If this problem persists, contact support with the reference code.",
        },
    )
```

**Explicación:**
- `create_error_reference()` genera ID único para correlación client/server
- `get_safe_error_message()` mapea excepciones a mensajes genéricos
- `log_error_with_context()` loguea detalles completos server-side
- `create_error_response()` es el entry point principal para handlers

#### Paso 2: Actualizar api.py para usar error handling

**Archivo a modificar:** `src/soni/server/api.py`

**Cambiar líneas 127-131 de:**
```python
except Exception as e:
    logger.error(f"Error processing message: {e}", exc_info=True)
    raise HTTPException(status_code=500, detail=f"Error processing message: {str(e)}") from e
```

**A:**
```python
except Exception as e:
    raise create_error_response(
        exception=e,
        user_id=request.user_id,
        endpoint="/message",
    ) from e
```

**Agregar import al inicio del archivo:**
```python
from soni.server.errors import create_error_response, global_exception_handler
```

**Registrar global handler después de crear app (línea ~70):**
```python
app.add_exception_handler(Exception, global_exception_handler)
```

#### Paso 3: Actualizar otros endpoints

**Archivo:** `src/soni/server/api.py`

Actualizar `/state/{user_id}` endpoint (si tiene try/except):
```python
except Exception as e:
    raise create_error_response(
        exception=e,
        user_id=user_id,
        endpoint=f"/state/{user_id}",
    ) from e
```

### TDD Cycle (MANDATORY)

#### Red Phase: Write Failing Tests

**Test file:** `tests/unit/server/test_error_handling.py`

```python
"""Tests for server error handling - ensures no sensitive data exposure."""

import pytest
from unittest.mock import Mock, patch
from fastapi.testclient import TestClient

from soni.server.errors import (
    create_error_reference,
    get_safe_error_message,
    get_http_status_for_exception,
    create_error_response,
)
from soni.core.errors import (
    ConfigError,
    ValidationError,
    FlowError,
    NLUError,
)


class TestErrorReferenceGeneration:
    """Test error reference creation."""

    def test_creates_unique_references(self):
        """Each call should produce unique reference."""
        refs = {create_error_reference() for _ in range(100)}
        assert len(refs) == 100  # All unique

    def test_reference_format(self):
        """Reference should follow ERR-XXXXXXXX format."""
        ref = create_error_reference()
        assert ref.startswith("ERR-")
        assert len(ref) == 12  # ERR- + 8 hex chars


class TestSafeErrorMessages:
    """Test error message sanitization."""

    def test_config_error_message_is_generic(self):
        """ConfigError should not expose details."""
        exc = ConfigError("secret/path/to/config.yaml not found")
        msg = get_safe_error_message(exc)
        assert "secret" not in msg.lower()
        assert "path" not in msg.lower()
        assert "configuration" in msg.lower()

    def test_validation_error_message_is_generic(self):
        """ValidationError should not expose field details."""
        exc = ValidationError("Field 'password' invalid: must be 8 chars")
        msg = get_safe_error_message(exc)
        assert "password" not in msg.lower()
        assert "invalid" in msg.lower()

    def test_unknown_exception_gets_default_message(self):
        """Unknown exceptions should get generic message."""
        exc = RuntimeError("Internal database connection string: postgres://...")
        msg = get_safe_error_message(exc)
        assert "postgres" not in msg.lower()
        assert "database" not in msg.lower()
        assert "internal" in msg.lower()

    def test_no_stack_trace_in_message(self):
        """Error messages should never contain stack traces."""
        try:
            raise ValueError("test error")
        except ValueError as e:
            msg = get_safe_error_message(e)
            assert "Traceback" not in msg
            assert "File" not in msg
            assert "line" not in msg


class TestHttpStatusMapping:
    """Test exception to HTTP status code mapping."""

    def test_validation_error_returns_400(self):
        """ValidationError should be client error."""
        assert get_http_status_for_exception(ValidationError("x")) == 400

    def test_nlu_error_returns_422(self):
        """NLUError should be unprocessable entity."""
        assert get_http_status_for_exception(NLUError("x")) == 422

    def test_config_error_returns_500(self):
        """ConfigError should be server error."""
        assert get_http_status_for_exception(ConfigError("x")) == 500

    def test_unknown_error_returns_500(self):
        """Unknown errors default to 500."""
        assert get_http_status_for_exception(RuntimeError("x")) == 500


class TestCreateErrorResponse:
    """Test HTTPException creation."""

    def test_response_contains_reference(self):
        """Response should include error reference."""
        exc = ValueError("secret info")
        response = create_error_response(exc)
        assert "reference" in response.detail
        assert response.detail["reference"].startswith("ERR-")

    def test_response_does_not_contain_original_message(self):
        """Original exception message should not be in response."""
        exc = ValueError("database password is xyz123")
        response = create_error_response(exc)
        assert "xyz123" not in str(response.detail)
        assert "password" not in str(response.detail).lower()

    def test_response_has_correct_status(self):
        """Status code should match exception type."""
        exc = ValidationError("x")
        response = create_error_response(exc)
        assert response.status_code == 400


class TestIntegrationNoExposure:
    """Integration tests verifying no data exposure in real API."""

    @pytest.fixture
    def client(self):
        """Create test client with error-producing runtime."""
        from soni.server.api import create_app
        app = create_app()
        return TestClient(app)

    def test_message_endpoint_error_does_not_expose_internals(self, client):
        """POST /message errors should not expose internal details."""
        # This will fail because runtime is not initialized
        response = client.post(
            "/message",
            json={"user_id": "test", "message": "hello"},
        )

        # Should get error but no internal details
        if response.status_code >= 400:
            body = response.json()
            assert "Traceback" not in str(body)
            assert "/Users/" not in str(body)
            assert "src/soni" not in str(body)
```

**Verify tests fail:**
```bash
uv run pytest tests/unit/server/test_error_handling.py -v
# Expected: FAILED (module not implemented yet)
```

#### Green Phase: Make Tests Pass

Implement the error handling module as described in Step 1-3.

```bash
uv run pytest tests/unit/server/test_error_handling.py -v
# Expected: PASSED
```

#### Refactor Phase

- Add docstrings to all public functions
- Ensure type hints are complete
- Consider adding structured logging (JSON format for production)

### Tests Requeridos

Ver sección TDD arriba.

### Criterios de Éxito

- [ ] Ningún mensaje de error expone rutas de archivos
- [ ] Ningún mensaje de error expone stack traces
- [ ] Ningún mensaje de error expone connection strings o secrets
- [ ] Cada error tiene reference ID único para debugging
- [ ] Server logs contienen detalles completos para debugging
- [ ] Tests de seguridad pasan
- [ ] Todos los tests pasan
- [ ] Linting pasa sin errores
- [ ] Type checking pasa sin errores

### Validación Manual

```bash
# Start server
uv run soni server --config examples/banking/soni.yaml

# Trigger error (sin runtime inicializado)
curl -X POST http://localhost:8000/message \
  -H "Content-Type: application/json" \
  -d '{"user_id": "test", "message": "hello"}'

# Verificar que la respuesta NO contiene:
# - Rutas de archivos (/Users/..., /home/..., src/soni/...)
# - Stack traces (Traceback, File "...", line X)
# - Detalles internos

# Verificar que la respuesta SÍ contiene:
# - Error reference (ERR-XXXXXXXX)
# - Mensaje genérico

# Verificar logs del servidor para detalles completos
```

### Referencias

- OWASP Information Exposure: https://owasp.org/www-community/vulnerabilities/Information_exposure_through_error_message
- FastAPI Exception Handling: https://fastapi.tiangolo.com/tutorial/handling-errors/
- Análisis original: Server API security issues

### Notas Adicionales

- Considerar agregar rate limiting de errores para prevenir brute force de error references
- En producción, considerar integración con servicio de monitoreo (Sentry, etc.)
- El error reference permite correlación entre cliente reportando problema y logs del servidor
