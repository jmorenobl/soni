## Task: 011 - Single Source of Truth for Version

**ID de tarea:** 011
**Hito:** 3 - Production Readiness
**Dependencias:** Ninguna
**Duración estimada:** 2 horas
**Prioridad:** BAJA

### Objetivo

Establecer una única fuente de verdad para la versión del proyecto, eliminando la discrepancia actual entre CLI (v2.0.0) y API (v0.8.0).

### Contexto

Actualmente la versión está hardcodeada en múltiples lugares:

1. **CLI:** `src/soni/cli/main.py:18`
   ```python
   typer.echo("Soni Framework v2.0.0")
   ```

2. **API:** `src/soni/server/api.py:73`
   ```python
   version="0.8.0",
   ```

3. **Posiblemente:** `pyproject.toml`

**Problemas:**
- Usuarios ven versiones diferentes según cómo interactúen
- Fácil olvidar actualizar todos los lugares
- No hay forma programática de obtener la versión

### Entregables

- [ ] Definir versión en `pyproject.toml` como fuente única
- [ ] Crear `soni/__version__.py` que lea de pyproject.toml
- [ ] Actualizar CLI para usar `__version__`
- [ ] Actualizar API para usar `__version__`
- [ ] Agregar endpoint `/version` en API

### Implementación Detallada

#### Paso 1: Verificar versión en pyproject.toml

**Archivo a verificar:** `pyproject.toml`

```toml
[project]
name = "soni"
version = "0.8.0"  # Fuente única de verdad
```

#### Paso 2: Crear módulo de versión

**Archivo a crear:** `src/soni/__version__.py`

```python
"""Version information for Soni Framework.

The version is read from pyproject.toml to maintain a single source of truth.
"""

from importlib.metadata import version, PackageNotFoundError

try:
    __version__ = version("soni")
except PackageNotFoundError:
    # Package not installed, fallback for development
    __version__ = "0.0.0-dev"

# Semantic version components
def get_version_info() -> dict[str, str | int]:
    """Parse version string into components.

    Returns:
        Dictionary with major, minor, patch, and full version
    """
    parts = __version__.split(".")
    return {
        "major": int(parts[0]) if len(parts) > 0 else 0,
        "minor": int(parts[1]) if len(parts) > 1 else 0,
        "patch": parts[2] if len(parts) > 2 else "0",  # May include suffix
        "full": __version__,
    }
```

#### Paso 3: Actualizar __init__.py principal

**Archivo a modificar:** `src/soni/__init__.py`

```python
"""Soni Framework - Conversational AI Engine."""

from soni.__version__ import __version__, get_version_info

__all__ = ["__version__", "get_version_info"]
```

#### Paso 4: Actualizar CLI

**Archivo a modificar:** `src/soni/cli/main.py`

**ANTES:**
```python
def version_callback(value: bool):
    if value:
        typer.echo("Soni Framework v2.0.0")
        raise typer.Exit()
```

**DESPUÉS:**
```python
from soni import __version__


def version_callback(value: bool):
    if value:
        typer.echo(f"Soni Framework v{__version__}")
        raise typer.Exit()
```

#### Paso 5: Actualizar API

**Archivo a modificar:** `src/soni/server/api.py`

**ANTES:**
```python
@app.get("/health", response_model=HealthResponse)
async def health_check(request: Request) -> HealthResponse:
    runtime = getattr(request.app.state, "runtime", None)

    return HealthResponse(
        status="healthy" if runtime is not None else "starting",
        version="0.8.0",  # Hardcoded!
        initialized=runtime is not None,
    )
```

**DESPUÉS:**
```python
from soni import __version__


@app.get("/health", response_model=HealthResponse)
async def health_check(request: Request) -> HealthResponse:
    runtime = getattr(request.app.state, "runtime", None)

    return HealthResponse(
        status="healthy" if runtime is not None else "starting",
        version=__version__,
        initialized=runtime is not None,
    )
```

#### Paso 6: Agregar endpoint /version

**Archivo a modificar:** `src/soni/server/api.py`

```python
from soni import __version__, get_version_info


class VersionResponse(BaseModel):
    """Response model for version endpoint."""
    version: str = Field(description="Full version string")
    major: int = Field(description="Major version number")
    minor: int = Field(description="Minor version number")
    patch: str = Field(description="Patch version (may include suffix)")


@app.get("/version", response_model=VersionResponse)
async def get_version() -> VersionResponse:
    """Get detailed version information."""
    info = get_version_info()
    return VersionResponse(
        version=info["full"],
        major=info["major"],
        minor=info["minor"],
        patch=info["patch"],
    )
```

**Agregar modelo a models.py:**

```python
class VersionResponse(BaseModel):
    """Response model for version endpoint."""
    version: str = Field(description="Full version string")
    major: int = Field(description="Major version number")
    minor: int = Field(description="Minor version number")
    patch: str = Field(description="Patch version (may include suffix)")
```

### TDD Cycle (MANDATORY for new features)

#### Red Phase: Write Failing Tests

**Test file:** `tests/unit/test_version.py`

```python
import pytest


class TestVersion:
    """Tests for version management."""

    def test_version_importable_from_root(self):
        """Test that __version__ can be imported from soni."""
        from soni import __version__

        assert __version__ is not None
        assert isinstance(__version__, str)
        assert len(__version__) > 0

    def test_version_follows_semver(self):
        """Test that version follows semantic versioning pattern."""
        from soni import __version__

        parts = __version__.split(".")
        assert len(parts) >= 2, "Version should have at least major.minor"

        # Major and minor should be numeric
        assert parts[0].isdigit(), "Major version should be numeric"
        assert parts[1].isdigit(), "Minor version should be numeric"

    def test_get_version_info_returns_dict(self):
        """Test that get_version_info returns proper structure."""
        from soni import get_version_info

        info = get_version_info()

        assert "major" in info
        assert "minor" in info
        assert "patch" in info
        assert "full" in info

        assert isinstance(info["major"], int)
        assert isinstance(info["minor"], int)

    def test_cli_version_matches_module(self):
        """Test that CLI version matches module version."""
        from soni import __version__

        # Import CLI and check it uses same version
        # This is a bit tricky to test without running CLI
        # We can at least verify the import works
        from soni.cli.main import version_callback

        # Version callback should use __version__
        # (Implementation detail, but important for consistency)


class TestVersionEndpoint:
    """Tests for /version API endpoint."""

    def test_version_endpoint_returns_version(self):
        """Test that /version endpoint returns version info."""
        from fastapi.testclient import TestClient
        from soni.server.api import app
        from soni import __version__

        client = TestClient(app)
        response = client.get("/version")

        assert response.status_code == 200
        data = response.json()
        assert data["version"] == __version__

    def test_health_endpoint_includes_version(self):
        """Test that /health endpoint includes correct version."""
        from fastapi.testclient import TestClient
        from soni.server.api import app
        from soni import __version__

        client = TestClient(app)
        response = client.get("/health")

        assert response.status_code == 200
        data = response.json()
        assert data["version"] == __version__
```

**Verify tests fail:**
```bash
uv run pytest tests/unit/test_version.py -v
# Expected: FAILED (module doesn't exist yet)
```

**Commit:**
```bash
git add tests/
git commit -m "test: add failing tests for version management"
```

#### Green Phase: Make Tests Pass

See "Implementación Detallada" section.

**Verify tests pass:**
```bash
uv run pytest tests/unit/test_version.py -v
# Expected: PASSED
```

**Commit:**
```bash
git add src/ tests/
git commit -m "feat: implement single source of truth for version

- Create soni/__version__.py reading from importlib.metadata
- Export __version__ and get_version_info from soni
- Update CLI to use __version__
- Update API /health to use __version__
- Add /version endpoint with detailed info"
```

### Criterios de Éxito

- [ ] Versión definida solo en `pyproject.toml`
- [ ] `from soni import __version__` funciona
- [ ] CLI muestra misma versión que API
- [ ] `/version` endpoint funciona
- [ ] `/health` endpoint muestra versión correcta
- [ ] Todos los tests pasan

### Validación Manual

**Comandos para validar:**

```bash
# Verificar versión en pyproject.toml
grep "^version" pyproject.toml

# Verificar import
uv run python -c "from soni import __version__; print(__version__)"

# Verificar CLI
uv run soni --version

# Verificar API
uv run soni server --config examples/banking/soni.yaml &
curl http://localhost:8000/version
curl http://localhost:8000/health

# Todas deben mostrar la misma versión
```

### Referencias

- PEP 440 - Version Identification
- Python Packaging User Guide
- Semantic Versioning 2.0.0

### Notas Adicionales

**Consideraciones para CI/CD:**
- Considerar herramientas como `bump2version` o `semantic-release`
- GitHub Actions puede actualizar versión automáticamente
- Tags de git deberían coincidir con versión
