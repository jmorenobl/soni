## Task: 5.2 - Structured Logging

**ID de tarea:** 502
**Hito:** Phase 5 - Production Readiness
**Dependencias:** Ninguna
**Duración estimada:** 2-3 horas

### Objetivo

Implement structured logging with context support, file rotation, and JSON formatting. This enables production debugging and observability.

### Contexto

Structured logging is essential for production systems. It provides consistent log formats, enables log aggregation and analysis, and supports contextual information for debugging. The logging module will be used throughout the framework for error tracking, performance monitoring, and audit trails.

**Reference:** [docs/implementation/05-phase-5-production.md](../../docs/implementation/05-phase-5-production.md) - Task 5.2

### Entregables

- [ ] `src/soni/observability/` directory created
- [ ] `src/soni/observability/__init__.py` created
- [ ] `src/soni/observability/logging.py` created with `setup_logging()` function
- [ ] `ContextLogger` class implemented
- [ ] File rotation configured
- [ ] JSON formatter support
- [ ] Tests passing in `tests/unit/test_logging.py`
- [ ] Mypy passes without errors

### Implementación Detallada

#### Paso 1: Create observability directory and __init__.py

**Archivo(s) a crear/modificar:** `src/soni/observability/__init__.py`

**Código específico:**

```python
"""Observability module for Soni Framework."""

from soni.observability.logging import ContextLogger, setup_logging

__all__ = ["ContextLogger", "setup_logging"]
```

**Explicación:**
- Create `src/soni/observability/` directory
- Create `__init__.py` to make it a package
- Export public API

#### Paso 2: Create logging.py File

**Archivo(s) a crear/modificar:** `src/soni/observability/logging.py`

**Código específico:**

```python
"""Structured logging configuration for Soni Framework."""

import logging
import logging.config
from typing import Any

try:
    from pythonjsonlogger import jsonlogger
except ImportError:
    jsonlogger = None  # Optional dependency


def setup_logging(level: str = "INFO") -> None:
    """
    Configure structured logging for Soni.

    Args:
        level: Log level (DEBUG, INFO, WARNING, ERROR)
    """
    config = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "structured": {
                "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
                "datefmt": "%Y-%m-%d %H:%M:%S",
            },
        },
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "formatter": "structured",
                "level": level,
            },
        },
        "loggers": {
            "soni": {
                "handlers": ["console"],
                "level": level,
                "propagate": False,
            },
        },
        "root": {
            "handlers": ["console"],
            "level": "WARNING",
        },
    }

    # Add file handler with rotation if jsonlogger is available
    if jsonlogger is not None:
        config["formatters"]["json"] = {
            "()": "pythonjsonlogger.jsonlogger.JsonFormatter",
            "format": "%(asctime)s %(name)s %(levelname)s %(message)s",
        }
        config["handlers"]["file"] = {
            "class": "logging.handlers.RotatingFileHandler",
            "filename": "soni.log",
            "maxBytes": 10485760,  # 10MB
            "backupCount": 5,
            "formatter": "json",
            "level": level,
        }
        config["loggers"]["soni"]["handlers"].append("file")

    logging.config.dictConfig(config)


class ContextLogger:
    """Logger with contextual information."""

    def __init__(self, name: str):
        """
        Initialize context logger.

        Args:
            name: Logger name (typically __name__)
        """
        self.logger = logging.getLogger(name)

    def with_context(self, **context: Any) -> logging.LoggerAdapter:
        """
        Add context to log messages.

        Args:
            **context: Context key-value pairs

        Returns:
            LoggerAdapter with context
        """
        return logging.LoggerAdapter(self.logger, context)
```

**Explicación:**
- Create `setup_logging()` function to configure logging
- Support both structured (console) and JSON (file) formats
- File rotation with configurable size (10MB) and backup count (5)
- Create `ContextLogger` class for contextual logging
- Make jsonlogger optional dependency (graceful degradation)

### Tests Requeridos

**Archivo de tests:** `tests/unit/test_logging.py`

**Tests específicos a implementar:**

```python
import logging
import pytest
from soni.observability.logging import ContextLogger, setup_logging

def test_logging_setup():
    """Test logging configuration."""
    # Arrange & Act
    setup_logging(level="DEBUG")

    # Assert
    logger = logging.getLogger("soni")
    assert logger.level == logging.DEBUG

def test_logging_setup_info_level():
    """Test logging setup with INFO level."""
    # Arrange & Act
    setup_logging(level="INFO")

    # Assert
    logger = logging.getLogger("soni")
    assert logger.level == logging.INFO

def test_context_logger():
    """Test ContextLogger with context."""
    # Arrange
    setup_logging(level="INFO")
    context_logger = ContextLogger("soni.test")

    # Act
    adapter = context_logger.with_context(user_id="test-user", flow="book_flight")

    # Assert
    assert isinstance(adapter, logging.LoggerAdapter)
    assert adapter.extra == {"user_id": "test-user", "flow": "book_flight"}

def test_context_logger_logging():
    """Test ContextLogger actually logs with context."""
    # Arrange
    setup_logging(level="DEBUG")
    context_logger = ContextLogger("soni.test")
    adapter = context_logger.with_context(user_id="test-user")

    # Act & Assert
    # Should not raise
    adapter.info("Test message")
```

### Criterios de Éxito

- [ ] `setup_logging()` function implemented
- [ ] `ContextLogger` class implemented
- [ ] File rotation configured (if jsonlogger available)
- [ ] Tests passing (`uv run pytest tests/unit/test_logging.py -v`)
- [ ] Mypy passes (`uv run mypy src/soni/observability/logging.py`)
- [ ] Ruff passes (`uv run ruff check src/soni/observability/logging.py`)

### Validación Manual

**Comandos para validar:**

```bash
# Type checking
uv run mypy src/soni/observability/logging.py

# Tests
uv run pytest tests/unit/test_logging.py -v

# Linting
uv run ruff check src/soni/observability/logging.py
uv run ruff format src/soni/observability/logging.py
```

**Resultado esperado:**
- Mypy shows no errors
- All tests pass
- Ruff shows no linting errors
- Logging can be configured and used throughout framework

### Referencias

- [docs/implementation/05-phase-5-production.md](../../docs/implementation/05-phase-5-production.md) - Task 5.2
- [Python logging documentation](https://docs.python.org/3/library/logging.html)

### Notas Adicionales

- Make jsonlogger optional (graceful degradation if not installed)
- File rotation uses 10MB max size and 5 backups
- ContextLogger uses LoggerAdapter for contextual information
- All log messages must be in English
- Structured format for console, JSON format for file (if available)
