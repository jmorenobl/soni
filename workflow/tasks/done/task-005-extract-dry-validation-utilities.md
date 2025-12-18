## Task: 005 - Extract DRY Validation Utilities for Node Factories

**ID de tarea:** 005
**Hito:** 2 - Quality Improvements
**Dependencias:** Task-003 (error types unification)
**Duración estimada:** 3 horas
**Prioridad:** MEDIA

### Objetivo

Extraer las validaciones de campos repetidas en los node factories a utilidades reutilizables, eliminando la duplicación de código (DRY violation) identificada en 7+ archivos del módulo compiler.

### Contexto

Actualmente cada node factory tiene código similar para validar campos requeridos:

```python
# say.py:23-24
if not step.message:
    raise ValueError(f"Step {step.step} of type 'say' missing required field 'message'")

# collect.py:25-26
if not step.slot:
    raise ValueError(f"Step {step.step} of type 'collect' missing required field 'slot'")

# action.py:23-24
if not step.call:
    raise ValueError(f"Step {step.step} of type 'action' missing required field 'call'")
```

Este patrón se repite en:
- `say.py` (message)
- `collect.py` (slot)
- `action.py` (call)
- `branch.py` (evaluate, cases)
- `set.py` (slot, value)
- `confirm.py` (prompt)
- `while_loop.py` (condition, do)

### Entregables

- [ ] Crear módulo `compiler/nodes/utils.py` con utilidades de validación
- [ ] Implementar `require_field()` y `require_fields()` helpers
- [ ] Refactorizar todos los node factories para usar utilidades
- [ ] Reducir líneas de código duplicado en ~50%
- [ ] Tests unitarios para utilidades

### Implementación Detallada

#### Paso 1: Crear módulo de utilidades

**Archivo a crear:** `src/soni/compiler/nodes/utils.py`

**Código específico:**

```python
"""Utility functions for node factories.

This module provides reusable validation and helper functions
to reduce code duplication across node factory implementations.
"""

from typing import Any, TypeVar

from soni.config.steps import StepConfig
from soni.core.errors import ValidationError

T = TypeVar("T")


def require_field(step: StepConfig, field: str, field_type: type[T] | None = None) -> T:
    """Validate that a required field exists and optionally check its type.

    Args:
        step: The step configuration to validate
        field: Name of the required field
        field_type: Optional type to validate against

    Returns:
        The field value

    Raises:
        ValidationError: If field is missing or has wrong type

    Example:
        >>> message = require_field(step, "message", str)
        >>> slot = require_field(step, "slot")
    """
    value = getattr(step, field, None)

    if value is None:
        raise ValidationError(
            f"Step '{step.step}' of type '{step.type}' is missing required field '{field}'"
        )

    if field_type is not None and not isinstance(value, field_type):
        raise ValidationError(
            f"Step '{step.step}' field '{field}' must be {field_type.__name__}, "
            f"got {type(value).__name__}"
        )

    return value


def require_fields(step: StepConfig, *fields: str) -> dict[str, Any]:
    """Validate multiple required fields at once.

    Args:
        step: The step configuration to validate
        *fields: Names of required fields

    Returns:
        Dictionary mapping field names to values

    Raises:
        ValidationError: If any field is missing (reports all missing fields)

    Example:
        >>> values = require_fields(step, "slot", "value")
        >>> slot, value = values["slot"], values["value"]
    """
    missing: list[str] = []
    values: dict[str, Any] = {}

    for field in fields:
        value = getattr(step, field, None)
        if value is None:
            missing.append(field)
        else:
            values[field] = value

    if missing:
        raise ValidationError(
            f"Step '{step.step}' of type '{step.type}' is missing required fields: "
            f"{', '.join(repr(f) for f in missing)}"
        )

    return values


def validate_non_empty(step: StepConfig, field: str, value: Any) -> None:
    """Validate that a field value is not empty (for lists, dicts, strings).

    Args:
        step: The step configuration (for error context)
        field: Name of the field being validated
        value: The value to check

    Raises:
        ValidationError: If value is empty
    """
    if not value:
        raise ValidationError(
            f"Step '{step.step}' field '{field}' cannot be empty"
        )


def get_optional_field(
    step: StepConfig,
    field: str,
    default: T = None
) -> T | Any:
    """Get an optional field with a default value.

    Args:
        step: The step configuration
        field: Name of the optional field
        default: Default value if field is missing

    Returns:
        The field value or default
    """
    value = getattr(step, field, None)
    return value if value is not None else default
```

#### Paso 2: Refactorizar say.py

**Archivo a modificar:** `src/soni/compiler/nodes/say.py`

**ANTES:**

```python
from soni.compiler.nodes.base import NodeFactory
from soni.config.steps import StepConfig

class SayNodeFactory(NodeFactory):
    def create(self, step: StepConfig, all_steps: list[StepConfig], step_index: int):
        if not step.message:
            raise ValueError(f"Step {step.step} of type 'say' missing required field 'message'")

        message = step.message
        # ... resto del código
```

**DESPUÉS:**

```python
from soni.compiler.nodes.base import NodeFactory
from soni.compiler.nodes.utils import require_field
from soni.config.steps import StepConfig

class SayNodeFactory(NodeFactory):
    def create(self, step: StepConfig, all_steps: list[StepConfig], step_index: int):
        message = require_field(step, "message", str)

        # ... resto del código (sin cambios)
```

#### Paso 3: Refactorizar collect.py

**ANTES:**

```python
if not step.slot:
    raise ValueError(f"Step {step.step} of type 'collect' missing required field 'slot'")

slot = step.slot
```

**DESPUÉS:**

```python
from soni.compiler.nodes.utils import require_field

slot = require_field(step, "slot", str)
```

#### Paso 4: Refactorizar action.py

**ANTES:**

```python
if not step.call:
    raise ValueError(f"Step {step.step} of type 'action' missing required field 'call'")

action_name = step.call
```

**DESPUÉS:**

```python
from soni.compiler.nodes.utils import require_field

action_name = require_field(step, "call", str)
```

#### Paso 5: Refactorizar branch.py

**ANTES:**

```python
if not step.evaluate:
    raise ValueError(f"Branch step '{step.step}' must have 'evaluate' field")
if not step.cases:
    raise ValueError(f"Branch step '{step.step}' must have 'cases' field")
if not isinstance(step.cases, dict):
    raise ValueError(f"Branch step '{step.step}' cases must be a dictionary")
```

**DESPUÉS:**

```python
from soni.compiler.nodes.utils import require_field, require_fields

values = require_fields(step, "evaluate", "cases")
evaluate = values["evaluate"]
cases = require_field(step, "cases", dict)  # Also validates type
```

#### Paso 6: Refactorizar set.py

**ANTES:**

```python
slot = step.slot
value = step.value

if not slot:
    raise ValueError(f"Set step '{step.step}' requires 'slot' field")
if value is None:
    raise ValueError(f"Set step '{step.step}' requires 'value' field")
```

**DESPUÉS:**

```python
from soni.compiler.nodes.utils import require_fields

values = require_fields(step, "slot", "value")
slot, value = values["slot"], values["value"]
```

#### Paso 7: Actualizar exports

**Archivo a modificar:** `src/soni/compiler/nodes/__init__.py`

**Agregar:**

```python
from soni.compiler.nodes.utils import (
    require_field,
    require_fields,
    validate_non_empty,
    get_optional_field,
)

__all__ = [
    # ... existentes
    "require_field",
    "require_fields",
    "validate_non_empty",
    "get_optional_field",
]
```

### TDD Cycle (MANDATORY for new features)

#### Red Phase: Write Failing Tests

**Test file:** `tests/unit/compiler/test_node_utils.py`

**Failing tests to write FIRST:**

```python
import pytest
from soni.core.errors import ValidationError
from soni.config.steps import StepConfig


class TestRequireField:
    """Tests for require_field utility."""

    def test_returns_value_when_field_exists(self):
        """Test that existing field value is returned."""
        from soni.compiler.nodes.utils import require_field

        step = StepConfig(step="greet", type="say", message="Hello")

        result = require_field(step, "message")

        assert result == "Hello"

    def test_raises_validation_error_when_field_missing(self):
        """Test that ValidationError is raised for missing field."""
        from soni.compiler.nodes.utils import require_field

        step = StepConfig(step="greet", type="say")  # No message

        with pytest.raises(ValidationError) as exc_info:
            require_field(step, "message")

        assert "missing required field 'message'" in str(exc_info.value)
        assert "greet" in str(exc_info.value)

    def test_validates_type_when_specified(self):
        """Test that type validation works."""
        from soni.compiler.nodes.utils import require_field

        step = StepConfig(step="check", type="branch", cases=["not", "a", "dict"])

        with pytest.raises(ValidationError) as exc_info:
            require_field(step, "cases", dict)

        assert "must be dict" in str(exc_info.value)

    def test_accepts_correct_type(self):
        """Test that correct type passes validation."""
        from soni.compiler.nodes.utils import require_field

        step = StepConfig(step="greet", type="say", message="Hello")

        result = require_field(step, "message", str)

        assert result == "Hello"


class TestRequireFields:
    """Tests for require_fields utility."""

    def test_returns_all_values_when_fields_exist(self):
        """Test that all field values are returned."""
        from soni.compiler.nodes.utils import require_fields

        step = StepConfig(step="assign", type="set", slot="name", value="John")

        result = require_fields(step, "slot", "value")

        assert result == {"slot": "name", "value": "John"}

    def test_raises_for_first_missing_field(self):
        """Test that ValidationError mentions all missing fields."""
        from soni.compiler.nodes.utils import require_fields

        step = StepConfig(step="assign", type="set")  # Missing both

        with pytest.raises(ValidationError) as exc_info:
            require_fields(step, "slot", "value")

        error_msg = str(exc_info.value)
        assert "'slot'" in error_msg
        assert "'value'" in error_msg

    def test_partial_missing_fields(self):
        """Test error when only some fields missing."""
        from soni.compiler.nodes.utils import require_fields

        step = StepConfig(step="assign", type="set", slot="name")  # Missing value

        with pytest.raises(ValidationError) as exc_info:
            require_fields(step, "slot", "value")

        error_msg = str(exc_info.value)
        assert "'value'" in error_msg
        assert "'slot'" not in error_msg  # slot exists


class TestValidateNonEmpty:
    """Tests for validate_non_empty utility."""

    def test_passes_for_non_empty_string(self):
        """Test that non-empty string passes."""
        from soni.compiler.nodes.utils import validate_non_empty

        step = StepConfig(step="test", type="say")

        validate_non_empty(step, "message", "Hello")  # Should not raise

    def test_raises_for_empty_string(self):
        """Test that empty string raises."""
        from soni.compiler.nodes.utils import validate_non_empty

        step = StepConfig(step="test", type="say")

        with pytest.raises(ValidationError) as exc_info:
            validate_non_empty(step, "message", "")

        assert "cannot be empty" in str(exc_info.value)

    def test_raises_for_empty_list(self):
        """Test that empty list raises."""
        from soni.compiler.nodes.utils import validate_non_empty

        step = StepConfig(step="loop", type="while")

        with pytest.raises(ValidationError):
            validate_non_empty(step, "do", [])


class TestGetOptionalField:
    """Tests for get_optional_field utility."""

    def test_returns_value_when_exists(self):
        """Test that existing value is returned."""
        from soni.compiler.nodes.utils import get_optional_field

        step = StepConfig(step="test", type="say", message="Hello")

        result = get_optional_field(step, "message", "Default")

        assert result == "Hello"

    def test_returns_default_when_missing(self):
        """Test that default is returned for missing field."""
        from soni.compiler.nodes.utils import get_optional_field

        step = StepConfig(step="test", type="say")

        result = get_optional_field(step, "nonexistent", "Default")

        assert result == "Default"

    def test_returns_none_by_default(self):
        """Test that None is default default."""
        from soni.compiler.nodes.utils import get_optional_field

        step = StepConfig(step="test", type="say")

        result = get_optional_field(step, "nonexistent")

        assert result is None
```

**Verify tests fail:**
```bash
uv run pytest tests/unit/compiler/test_node_utils.py -v
# Expected: FAILED (module doesn't exist yet)
```

**Commit:**
```bash
git add tests/
git commit -m "test: add failing tests for node factory validation utilities"
```

#### Green Phase: Make Tests Pass

See "Implementación Detallada" section for implementation steps.

**Verify tests pass:**
```bash
uv run pytest tests/unit/compiler/test_node_utils.py -v
uv run pytest tests/unit/compiler/ -v  # All compiler tests
# Expected: PASSED
```

**Commit:**
```bash
git add src/ tests/
git commit -m "feat: add validation utilities for node factories

- Create compiler/nodes/utils.py with reusable validation
- Implement require_field, require_fields, validate_non_empty
- Implement get_optional_field for optional values
- Full test coverage for all utilities"
```

#### Refactor Phase: Improve Design

- Refactor all node factories to use new utilities
- Remove duplicate validation code
- Ensure consistent error messages
- Tests must still pass!

**Commit:**
```bash
git add src/
git commit -m "refactor: use validation utilities in all node factories

- Refactor say.py, collect.py, action.py
- Refactor branch.py, set.py, confirm.py
- Reduce duplicate code by ~50%
- Consistent error messages across factories"
```

### Criterios de Éxito

- [ ] `compiler/nodes/utils.py` creado con utilidades
- [ ] Todas las node factories usan las utilidades
- [ ] No hay código de validación duplicado
- [ ] Mensajes de error son consistentes
- [ ] Reducción de líneas de código duplicado ~50%
- [ ] Todos los tests pasan
- [ ] Linting pasa sin errores
- [ ] Type checking pasa sin errores

### Validación Manual

**Comandos para validar:**

```bash
# Verificar que no hay validaciones duplicadas
grep -r "if not step\." src/soni/compiler/nodes/*.py | wc -l
# Esperado: número reducido significativamente

# Verificar que utilities se usan
grep -r "require_field\|require_fields" src/soni/compiler/nodes/*.py
# Esperado: aparece en todos los factories

# Ejecutar todos los tests del compiler
uv run pytest tests/unit/compiler/ -v
```

**Resultado esperado:**
- Menos de 5 validaciones inline restantes
- Utilities usadas en 6+ archivos
- Todos los tests pasan

### Referencias

- `src/soni/compiler/nodes/*.py` - Factories a refactorizar
- `src/soni/core/errors.py` - ValidationError
- DRY principle documentation

### Notas Adicionales

**Beneficios esperados:**
- Código más mantenible
- Mensajes de error consistentes
- Facilita agregar nuevos tipos de step
- Reduce posibilidad de errores al modificar validaciones

**Consideraciones:**
- Mantener backward compatibility con tests existentes
- Documentar utilidades para futuros desarrolladores
