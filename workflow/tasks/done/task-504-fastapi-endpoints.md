## Task: 5.4 - FastAPI Endpoints

**ID de tarea:** 504
**Hito:** Phase 5 - Production Readiness
**Dependencias:** Task 501 (Error Handling), Task 502 (Logging)
**Duración estimada:** 2-3 horas

### Objetivo

Verify existing FastAPI endpoints meet Phase 5 requirements. Enhance if needed to integrate error handling and structured logging.

### Contexto

The FastAPI server is the production interface for the Soni framework. Existing endpoints should be verified and enhanced to use structured logging and proper error handling. The server already has `/health` and `/chat/{user_id}` endpoints that need verification.

**Reference:** [docs/implementation/05-phase-5-production.md](../../docs/implementation/05-phase-5-production.md) - Task 5.4

### Entregables

- [ ] Review existing `src/soni/server/api.py`
- [ ] Verify `/health` endpoint works correctly
- [ ] Verify `/chat/{user_id}` endpoint works correctly
- [ ] Integrate structured logging if not already present
- [ ] Verify error handling is comprehensive
- [ ] Tests passing in `tests/integration/test_api.py`
- [ ] Mypy passes without errors

### Implementación Detallada

#### Paso 1: Review Existing API

**Archivo(s) a revisar:** `src/soni/server/api.py`

**Explicación:**
- Review existing endpoints
- Check if structured logging is used
- Verify error handling is comprehensive
- Check if health check provides useful information

#### Paso 2: Enhance if Needed

**Archivo(s) a modificar:** `src/soni/server/api.py` (if needed)

**Explicación:**
- Integrate structured logging from Task 502
- Ensure error responses are properly formatted
- Add any missing error handling
- Verify health check includes runtime status

### Tests Requeridos

**Archivo de tests:** `tests/integration/test_api.py` (may already exist)

**Tests específicos a verificar/agregar:**

```python
import pytest
from fastapi.testclient import TestClient
from soni.server.api import app

@pytest.fixture
def client():
    """Create test client."""
    return TestClient(app)

def test_health_check(client):
    """Test health check endpoint."""
    # Act
    response = client.get("/health")

    # Assert
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "version" in data

def test_health_check_structure(client):
    """Test health check returns correct structure."""
    # Act
    response = client.get("/health")

    # Assert
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data["status"], str)
    assert isinstance(data["version"], str)

# Note: Full message test requires mocking RuntimeLoop
# This is complex and may already be tested elsewhere
```

### Criterios de Éxito

- [ ] Health check endpoint works correctly
- [ ] Error handling is comprehensive
- [ ] Structured logging is used (if Task 502 completed)
- [ ] Tests passing (`uv run pytest tests/integration/test_api.py -v`)
- [ ] Mypy passes (`uv run mypy src/soni/server/api.py`)
- [ ] Ruff passes (`uv run ruff check src/soni/server/api.py`)

### Validación Manual

**Comandos para validar:**

```bash
# Type checking
uv run mypy src/soni/server/api.py

# Tests
uv run pytest tests/integration/test_api.py -v

# Linting
uv run ruff check src/soni/server/api.py
uv run ruff format src/soni/server/api.py

# Start server manually
uv run uvicorn soni.server.api:app --reload
```

**Resultado esperado:**
- Mypy shows no errors
- All tests pass
- Ruff shows no linting errors
- Server starts without errors
- Health check returns correct response

### Referencias

- [docs/implementation/05-phase-5-production.md](../../docs/implementation/05-phase-5-production.md) - Task 5.4
- [FastAPI documentation](https://fastapi.tiangolo.com/)

### Notas Adicionales

- Existing API is likely already well-implemented
- Focus on verification and integration of Task 501/502 features
- Use TestClient from FastAPI for testing
- Health check should verify runtime is initialized
- All error messages must be in English
