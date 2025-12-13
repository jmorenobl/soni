## Task: DM-005 - Validate NLU Result Schema

**ID de tarea:** DM-005
**Hito:** Dialog Manager Enterprise Hardening
**Dependencias:** Ninguna
**Duración estimada:** 3 horas

### Objetivo

Agregar validación defensiva del `nlu_result` al entrar en el router para garantizar type safety y mejorar mensajes de error cuando el NLU devuelve datos inesperados.

### Contexto

El código actual accede a campos de `nlu_result` asumiendo su estructura:

```python
message_type = nlu_result.get("message_type")
slots = nlu_result.get("slots", [])
command = nlu_result.get("command")
```

Si el NLU devuelve algo inesperado (None, string malformado, estructura diferente), el código puede:
- Fallar silenciosamente con None
- Lanzar AttributeError/KeyError crípticos
- Comportarse de forma impredecible

Para producción enterprise, necesitamos:
- Validación con Pydantic al boundary
- Type narrowing para el resto del código
- Mensajes de error claros y actionables

### Entregables

- [ ] Crear/extender modelo Pydantic `NLUResult` para validación
- [ ] Agregar función `validate_nlu_result()` en routing
- [ ] Aplicar validación al inicio de `route_after_understand`
- [ ] Mejorar manejo de errores con mensajes claros
- [ ] Tests para casos de NLU result malformados

### Implementación Detallada

#### Paso 1: Definir modelo Pydantic estricto

**Archivo(s) a crear/modificar:** `src/soni/core/models.py` o `src/soni/dm/routing.py`

```python
from pydantic import BaseModel, Field, field_validator
from typing import Any


class SlotValue(BaseModel):
    """Validated slot value from NLU."""
    name: str
    value: Any
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)


class ValidatedNLUResult(BaseModel):
    """Pydantic model for validated NLU result.

    Ensures all required fields are present and correctly typed
    before routing logic processes the result.
    """
    message_type: str
    command: str | None = None
    slots: list[SlotValue] = Field(default_factory=list)
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    raw_text: str | None = None

    @field_validator("message_type")
    @classmethod
    def normalize_message_type(cls, v: Any) -> str:
        """Normalize message_type to lowercase string."""
        if v is None:
            raise ValueError("message_type cannot be None")
        # Handle enum types
        if hasattr(v, "value"):
            v = v.value
        return str(v).lower()

    @field_validator("slots", mode="before")
    @classmethod
    def ensure_slots_list(cls, v: Any) -> list:
        """Ensure slots is always a list."""
        if v is None:
            return []
        if not isinstance(v, list):
            return [v]
        return v

    model_config = {"extra": "allow"}  # Allow extra fields for forward compat
```

#### Paso 2: Crear función de validación

```python
from pydantic import ValidationError


class NLUResultValidationError(Exception):
    """Raised when NLU result fails validation."""

    def __init__(self, original_error: ValidationError, nlu_result: Any):
        self.original_error = original_error
        self.nlu_result = nlu_result
        super().__init__(self._format_message())

    def _format_message(self) -> str:
        return (
            f"Invalid NLU result structure. "
            f"Errors: {self.original_error.error_count()} validation errors. "
            f"First error: {self.original_error.errors()[0]['msg']}"
        )


def validate_nlu_result(nlu_result: dict[str, Any] | None) -> ValidatedNLUResult | None:
    """Validate and parse NLU result with clear error messages.

    Args:
        nlu_result: Raw NLU result dict from state

    Returns:
        ValidatedNLUResult if valid, None if nlu_result is None

    Raises:
        NLUResultValidationError: If nlu_result is malformed
    """
    if nlu_result is None:
        return None

    try:
        return ValidatedNLUResult.model_validate(nlu_result)
    except ValidationError as e:
        logger.error(
            f"NLU result validation failed: {e.error_count()} errors",
            extra={
                "nlu_result_keys": list(nlu_result.keys()) if isinstance(nlu_result, dict) else None,
                "nlu_result_type": type(nlu_result).__name__,
                "errors": e.errors(),
            }
        )
        raise NLUResultValidationError(e, nlu_result) from e
```

#### Paso 3: Integrar en route_after_understand

```python
def route_after_understand(state: DialogueStateType) -> str:
    """Route based on NLU result."""
    raw_nlu = state.get("nlu_result")

    # Validate at boundary
    try:
        nlu_result = validate_nlu_result(raw_nlu)
    except NLUResultValidationError as e:
        logger.error(f"Cannot route: {e}")
        return "generate_response"  # Graceful fallback

    if nlu_result is None:
        return "generate_response"

    # Now we have type-safe access
    message_type = nlu_result.message_type  # str, guaranteed
    slots = nlu_result.slots  # list[SlotValue], guaranteed
    command = nlu_result.command  # str | None, guaranteed

    # ... rest of routing logic with type safety
```

### TDD Cycle (MANDATORY for new features)

#### Red Phase: Write Failing Tests

**Test file:** `tests/unit/dm/test_nlu_validation.py`

```python
import pytest
from soni.dm.routing import validate_nlu_result, NLUResultValidationError


class TestNLUResultValidation:
    """Test NLU result validation."""

    def test_valid_result_passes(self):
        """Valid NLU result should validate successfully."""
        nlu = {
            "message_type": "slot_value",
            "slots": [{"name": "city", "value": "Madrid"}],
            "command": "book_flight",
        }
        result = validate_nlu_result(nlu)
        assert result is not None
        assert result.message_type == "slot_value"

    def test_none_result_returns_none(self):
        """None NLU result should return None."""
        assert validate_nlu_result(None) is None

    def test_missing_message_type_raises(self):
        """Missing message_type should raise validation error."""
        nlu = {"slots": [], "command": "test"}
        with pytest.raises(NLUResultValidationError):
            validate_nlu_result(nlu)

    def test_enum_message_type_normalized(self):
        """Enum message_type should be normalized to string."""
        from enum import Enum

        class MockType(Enum):
            SLOT_VALUE = "slot_value"

        nlu = {"message_type": MockType.SLOT_VALUE}
        result = validate_nlu_result(nlu)
        assert result.message_type == "slot_value"

    def test_slots_none_becomes_empty_list(self):
        """slots=None should become empty list."""
        nlu = {"message_type": "test", "slots": None}
        result = validate_nlu_result(nlu)
        assert result.slots == []

    def test_extra_fields_allowed(self):
        """Extra fields should be allowed for forward compat."""
        nlu = {
            "message_type": "test",
            "future_field": "value",
            "another_new_field": 123,
        }
        result = validate_nlu_result(nlu)
        assert result is not None
```

### Criterios de Éxito

- [ ] `ValidatedNLUResult` modelo Pydantic implementado
- [ ] `validate_nlu_result()` función con error handling claro
- [ ] `NLUResultValidationError` con mensajes actionables
- [ ] Validación aplicada al inicio de `route_after_understand`
- [ ] Tests cubren: valid, None, missing fields, enum types, extra fields
- [ ] Fallback graceful a `generate_response` si validación falla

### Validación Manual

```bash
uv run pytest tests/unit/dm/test_nlu_validation.py -v
uv run pytest tests/integration/ -v  # Verify no regressions

# Test with malformed NLU in debug mode
SONI_LOG_LEVEL=DEBUG uv run python -c "
from soni.dm.routing import validate_nlu_result
validate_nlu_result({'bad': 'data'})
"
```

### Referencias

- [Pydantic V2 Validators](https://docs.pydantic.dev/latest/concepts/validators/)
- [Defensive Programming](https://en.wikipedia.org/wiki/Defensive_programming)

### Notas Adicionales

- `extra="allow"` permite forward compatibility con nuevos campos del NLU
- Considerar caching de validación si hay overhead de performance
- El fallback a `generate_response` evita crashes en producción pero debe alertar
