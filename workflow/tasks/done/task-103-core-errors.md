## Task: 1.3 - Core Errors

**ID de tarea:** 103
**Hito:** Phase 1 - Core Foundation
**Dependencias:** Ninguna
**Duración estimada:** 1-2 horas

### Objetivo

Define exception hierarchy for the framework to enable proper error handling with specific exception types and context information.

### Contexto

A well-defined exception hierarchy allows for better error handling, debugging, and user feedback. All framework errors should inherit from a base SoniError class and include context information for better error messages.

**Reference:** [docs/implementation/01-phase-1-foundation.md](../../docs/implementation/01-phase-1-foundation.md) - Task 1.3

### Entregables

- [ ] Base SoniError class defined with context support
- [ ] NLUError exception class
- [ ] ValidationError exception class
- [ ] ActionNotFoundError exception class
- [ ] FlowStackLimitError exception class
- [ ] ConfigurationError exception class
- [ ] PersistenceError exception class
- [ ] CompilationError exception class
- [ ] Context support working (error messages include context)
- [ ] Tests passing in `tests/unit/test_errors.py`
- [ ] Docstrings present for all error classes

### Implementación Detallada

#### Paso 1: Create errors.py File

**Archivo(s) a crear/modificar:** `src/soni/core/errors.py`

**Código específico:**

```python
from typing import Any

class SoniError(Exception):
    """Base exception for all Soni errors."""

    def __init__(self, message: str, **context: Any) -> None:
        super().__init__(message)
        self.message = message
        self.context = context

    def __str__(self) -> str:
        if self.context:
            ctx_str = ", ".join(f"{k}={v}" for k, v in self.context.items())
            return f"{self.message} ({ctx_str})"
        return self.message

class NLUError(SoniError):
    """Error during NLU processing."""
    pass

class ValidationError(SoniError):
    """Error during validation."""
    pass

class ActionNotFoundError(SoniError):
    """Action not found in registry."""
    pass

class FlowStackLimitError(SoniError):
    """Flow stack depth limit exceeded."""
    pass

class ConfigurationError(SoniError):
    """Configuration error."""
    pass

class PersistenceError(SoniError):
    """Error during state persistence."""
    pass

class CompilationError(SoniError):
    """Error during YAML compilation."""
    pass
```

**Explicación:**
- Create base SoniError class with context support
- Override `__str__` to include context in error messages
- Create specific error classes for different error types
- All specific errors inherit from SoniError
- Use `pass` for simple inheritance (no additional logic needed)

#### Paso 2: Create Unit Tests

**Archivo(s) a crear/modificar:** `tests/unit/test_errors.py`

**Código específico:**

```python
import pytest
from soni.core.errors import (
    SoniError,
    ValidationError,
    FlowStackLimitError,
    NLUError,
    ActionNotFoundError,
    ConfigurationError,
    PersistenceError,
    CompilationError
)

def test_base_error_with_context():
    """Test SoniError includes context in message."""
    # Arrange & Act
    error = SoniError(
        "Something failed",
        user_id="123",
        flow="book_flight"
    )

    # Assert
    assert "Something failed" in str(error)
    assert "user_id=123" in str(error)
    assert "flow=book_flight" in str(error)

def test_validation_error_inheritance():
    """Test ValidationError is a SoniError."""
    # Arrange & Act
    error = ValidationError("Invalid slot", slot="origin", value="invalid")

    # Assert
    assert isinstance(error, SoniError)
    assert "Invalid slot" in str(error)
    assert "slot=origin" in str(error)
```

**Explicación:**
- Test base error with context
- Test error inheritance
- Test error message formatting with context
- Test all specific error types

### Tests Requeridos

**Archivo de tests:** `tests/unit/test_errors.py`

**Tests específicos a implementar:**

```python
import pytest
from soni.core.errors import (
    SoniError,
    ValidationError,
    FlowStackLimitError,
    NLUError,
    ActionNotFoundError,
    ConfigurationError,
    PersistenceError,
    CompilationError
)

def test_base_error_with_context():
    """Test SoniError includes context in message."""
    # Arrange & Act
    error = SoniError(
        "Something failed",
        user_id="123",
        flow="book_flight"
    )

    # Assert
    assert "Something failed" in str(error)
    assert "user_id=123" in str(error)
    assert "flow=book_flight" in str(error)

def test_base_error_without_context():
    """Test SoniError without context."""
    # Arrange & Act
    error = SoniError("Simple error")

    # Assert
    assert str(error) == "Simple error"
    assert error.context == {}

def test_validation_error_inheritance():
    """Test ValidationError is a SoniError."""
    # Arrange & Act
    error = ValidationError("Invalid slot", slot="origin", value="invalid")

    # Assert
    assert isinstance(error, SoniError)
    assert "Invalid slot" in str(error)
    assert "slot=origin" in str(error)
    assert "value=invalid" in str(error)

def test_all_error_types_inherit_from_soni_error():
    """Test all specific error types inherit from SoniError."""
    # Arrange
    error_types = [
        NLUError,
        ValidationError,
        ActionNotFoundError,
        FlowStackLimitError,
        ConfigurationError,
        PersistenceError,
        CompilationError
    ]

    # Act & Assert
    for error_type in error_types:
        error = error_type("Test error", test="value")
        assert isinstance(error, SoniError)
        assert "Test error" in str(error)
```

### Criterios de Éxito

- [ ] All error classes defined
- [ ] Context support working (error messages include context)
- [ ] Tests passing (`uv run pytest tests/unit/test_errors.py -v`)
- [ ] Docstrings present for all error classes
- [ ] Ruff passes (`uv run ruff check src/soni/core/errors.py`)

### Validación Manual

**Comandos para validar:**

```bash
# Tests
uv run pytest tests/unit/test_errors.py -v

# Linting
uv run ruff check src/soni/core/errors.py
uv run ruff format src/soni/core/errors.py
```

**Resultado esperado:**
- All tests pass
- Ruff shows no linting errors
- Error messages include context when provided
- All error types properly inherit from SoniError

### Referencias

- [docs/implementation/01-phase-1-foundation.md](../../docs/implementation/01-phase-1-foundation.md) - Task 1.3
- [Python Exception documentation](https://docs.python.org/3/tutorial/errors.html)

### Notas Adicionales

- Base SoniError class supports context via **kwargs
- Context is included in error message string representation
- All specific errors inherit from SoniError
- Error messages must be in English (per project conventions)
- Context can include any key-value pairs for debugging
