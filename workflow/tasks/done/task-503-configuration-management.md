## Task: 5.3 - Configuration Management

**ID de tarea:** 503
**Hito:** Phase 5 - Production Readiness
**Dependencias:** Ninguna
**Duración estimada:** 1-2 horas

### Objetivo

Verify existing configuration management meets Phase 5 requirements. Enhance if needed to ensure Pydantic validation works correctly and configuration loading handles errors gracefully.

### Contexto

Configuration management is critical for production deployments. The existing `src/soni/core/config.py` already has comprehensive Pydantic models and validation. This task verifies it meets Phase 5 requirements and enhances if necessary.

**Reference:** [docs/implementation/05-phase-5-production.md](../../docs/implementation/05-phase-5-production.md) - Task 5.3

### Entregables

- [ ] Review existing `src/soni/core/config.py`
- [ ] Verify Pydantic validation is working correctly
- [ ] Verify error handling in configuration loading
- [ ] Add enhancements if needed
- [ ] Tests passing in `tests/unit/test_config.py`
- [ ] Mypy passes without errors

### Implementación Detallada

#### Paso 1: Review Existing Configuration

**Archivo(s) a revisar:** `src/soni/core/config.py`

**Explicación:**
- Review existing `SoniConfig`, `Settings`, and related Pydantic models
- Verify validation is comprehensive
- Check error handling in `load_and_validate()` and `from_yaml()`
- Ensure default values are appropriate

#### Paso 2: Enhance if Needed

**Archivo(s) a modificar:** `src/soni/core/config.py` (if needed)

**Explicación:**
- Add any missing validation
- Improve error messages if needed
- Ensure all configuration paths are validated

### Tests Requeridos

**Archivo de tests:** `tests/unit/test_config.py` (may already exist)

**Tests específicos a verificar/agregar:**

```python
import pytest
from pathlib import Path
from soni.core.config import ConfigLoader, SoniConfig
from soni.core.errors import ConfigurationError

def test_load_config_valid(tmp_path):
    """Test loading valid configuration."""
    # Arrange
    config_file = tmp_path / "config.yaml"
    config_file.write_text("""
version: "1.0"
settings:
  models:
    nlu:
      provider: openai
      model: gpt-4o-mini
      temperature: 0.0
flows: {}
slots: {}
actions: {}
""")

    # Act
    config = SoniConfig.from_yaml(config_file)

    # Assert
    assert config.version == "1.0"
    assert config.settings.models.nlu.model == "gpt-4o-mini"

def test_load_config_invalid_raises(tmp_path):
    """Test invalid configuration raises error."""
    # Arrange
    config_file = tmp_path / "config.yaml"
    config_file.write_text("""
version: "1.0"
settings:
  models:
    nlu:
      provider: openai
      model: gpt-4o-mini
      temperature: -1.0  # Invalid: negative temperature
flows: {}
slots: {}
actions: {}
""")

    # Act & Assert
    with pytest.raises(Exception):  # Pydantic ValidationError
        SoniConfig.from_yaml(config_file)

def test_load_config_missing_file():
    """Test loading non-existent file raises error."""
    # Arrange
    non_existent = Path("/non/existent/config.yaml")

    # Act & Assert
    with pytest.raises(ConfigurationError):
        ConfigLoader.load(non_existent)

def test_config_default_values():
    """Test configuration has appropriate default values."""
    # Arrange & Act
    config = SoniConfig(
        version="1.0",
        settings={
            "models": {
                "nlu": {
                    "provider": "openai",
                    "model": "gpt-4o-mini",
                }
            }
        },
        flows={},
        slots={},
        actions={},
    )

    # Assert
    assert config.settings.persistence.backend == "sqlite"
    assert config.settings.logging.level == "INFO"
```

### Criterios de Éxito

- [ ] Configuration loading works correctly
- [ ] Pydantic validation catches invalid configurations
- [ ] Error messages are clear and helpful
- [ ] Tests passing (`uv run pytest tests/unit/test_config.py -v`)
- [ ] Mypy passes (`uv run mypy src/soni/core/config.py`)
- [ ] Ruff passes (`uv run ruff check src/soni/core/config.py`)

### Validación Manual

**Comandos para validar:**

```bash
# Type checking
uv run mypy src/soni/core/config.py

# Tests
uv run pytest tests/unit/test_config.py -v

# Linting
uv run ruff check src/soni/core/config.py
uv run ruff format src/soni/core/config.py
```

**Resultado esperado:**
- Mypy shows no errors
- All tests pass
- Ruff shows no linting errors
- Configuration validation works correctly

### Referencias

- [docs/implementation/05-phase-5-production.md](../../docs/implementation/05-phase-5-production.md) - Task 5.3
- [Pydantic documentation](https://docs.pydantic.dev/)

### Notas Adicionales

- Existing configuration management is likely already comprehensive
- Focus on verification and minor enhancements if needed
- Ensure all error paths are tested
- Default values should be production-appropriate
