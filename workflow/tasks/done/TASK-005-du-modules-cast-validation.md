## Task: TASK-005 - DU Modules: Reemplazar cast() con Validación Runtime

**ID de tarea:** 005
**Hito:** Type Safety Improvements
**Dependencias:** Ninguna
**Duración estimada:** 2 horas
**Prioridad:** CRÍTICA

### Objetivo

Reemplazar el uso de `cast()` sin validación en los módulos DU con validación runtime apropiada, previniendo errores silenciosos cuando DSPy retorna estructuras inesperadas.

### Contexto

El análisis identificó uso problemático de `cast()` en `du/modules.py:66` y `du/slot_extractor.py:162`:

```python
# modules.py:66
return cast(NLUOutput, result.result)

# slot_extractor.py:162
return cast(SlotExtractionResult, result.result)
```

**Problemas:**
1. `cast()` NO valida en runtime - solo informa al type checker
2. Si DSPy retorna estructura incorrecta, código continúa con datos inválidos
3. Errores se manifiestan lejos del punto de origen, difíciles de debuggear
4. DSPy usa `__getattr__` dinámico, sin garantías de tipo

### Entregables

- [ ] Crear función de validación para resultados DSPy
- [ ] Reemplazar `cast(NLUOutput, ...)` con validación
- [ ] Reemplazar `cast(SlotExtractionResult, ...)` con validación
- [ ] Agregar logging cuando validación falla
- [ ] Tests verificando validación correcta

### Implementación Detallada

#### Paso 1: Crear utilidad de validación en du/base.py

**Archivo a modificar:** `src/soni/du/base.py`

**Agregar al final del archivo:**
```python
from typing import TypeVar, Type
from pydantic import BaseModel, ValidationError as PydanticValidationError
import logging

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)


def validate_dspy_result(
    result: Any,
    expected_type: Type[T],
    context: str = "DSPy result",
) -> T:
    """Validate and convert DSPy Prediction result to expected Pydantic model.

    DSPy returns Prediction objects with dynamic attributes. This function
    validates that the result matches the expected schema and converts it
    to a proper Pydantic model.

    Args:
        result: The result attribute from DSPy Prediction (result.result)
        expected_type: The Pydantic model class to validate against
        context: Description for error messages

    Returns:
        Validated instance of expected_type

    Raises:
        TypeError: If result is None or wrong type
        ValidationError: If result doesn't match expected schema

    Example:
        >>> result = await self.extractor.acall(...)
        >>> output = validate_dspy_result(result.result, NLUOutput, "NLU extraction")
    """
    if result is None:
        logger.error(f"{context}: result is None")
        raise TypeError(f"{context} returned None - expected {expected_type.__name__}")

    # If already the expected type, return as-is
    if isinstance(result, expected_type):
        return result

    # If it's a dict, try to validate with Pydantic
    if isinstance(result, dict):
        try:
            return expected_type.model_validate(result)
        except PydanticValidationError as e:
            logger.error(f"{context}: validation failed - {e}")
            raise

    # If it has a model_dump method (Pydantic-like), use that
    if hasattr(result, "model_dump"):
        try:
            data = result.model_dump()
            return expected_type.model_validate(data)
        except PydanticValidationError as e:
            logger.error(f"{context}: validation failed after model_dump - {e}")
            raise

    # If it has _store (DSPy Example/Prediction), extract from there
    if hasattr(result, "_store"):
        try:
            # DSPy stores the actual data in _store dict
            data = dict(result._store)
            return expected_type.model_validate(data)
        except PydanticValidationError as e:
            logger.error(f"{context}: validation failed from _store - {e}")
            raise

    # Try direct attribute access as last resort
    try:
        # Extract attributes matching model fields
        data = {}
        for field_name in expected_type.model_fields:
            if hasattr(result, field_name):
                data[field_name] = getattr(result, field_name)

        if data:
            return expected_type.model_validate(data)
    except PydanticValidationError as e:
        logger.error(f"{context}: validation failed from attributes - {e}")
        raise

    # Give up with informative error
    result_type = type(result).__name__
    logger.error(
        f"{context}: cannot convert {result_type} to {expected_type.__name__}. "
        f"Result: {result!r}"
    )
    raise TypeError(
        f"{context}: expected {expected_type.__name__}, got {result_type}"
    )


def safe_extract_result(
    result: Any,
    expected_type: Type[T],
    default_factory: callable,
    context: str = "DSPy result",
) -> T:
    """Safely extract and validate DSPy result with fallback to default.

    Use this for cases where you want graceful degradation instead of exceptions.

    Args:
        result: The result attribute from DSPy Prediction
        expected_type: The Pydantic model class to validate against
        default_factory: Callable that returns a default instance
        context: Description for error messages

    Returns:
        Validated instance of expected_type, or default if validation fails
    """
    try:
        return validate_dspy_result(result, expected_type, context)
    except (TypeError, PydanticValidationError) as e:
        logger.warning(
            f"{context}: using default due to validation failure - {e}"
        )
        return default_factory()
```

#### Paso 2: Actualizar modules.py para usar validación

**Archivo a modificar:** `src/soni/du/modules.py`

**Cambiar acall() de:**
```python
async def acall(
    self,
    user_message: str,
    context: DialogueContext,
    history: list[dict[str, str]] | None = None,
) -> NLUOutput:
    try:
        # ... call extractor ...
        result = await self.extractor.acall(...)
        return cast(NLUOutput, result.result)
    except Exception as e:
        logger.error(f"NLU extraction failed: {e}", exc_info=True)
        return NLUOutput(commands=[], confidence=0.0)
```

**A:**
```python
async def acall(
    self,
    user_message: str,
    context: DialogueContext,
    history: list[dict[str, str]] | None = None,
) -> NLUOutput:
    from soni.du.base import safe_extract_result

    try:
        result = await self.extractor.acall(
            user_message=user_message,
            context=context,
            history=history or [],
        )

        return safe_extract_result(
            result.result,
            NLUOutput,
            default_factory=lambda: NLUOutput(commands=[], confidence=0.0),
            context="NLU extraction",
        )

    except Exception as e:
        logger.error(f"NLU extraction failed: {e}", exc_info=True)
        return NLUOutput(commands=[], confidence=0.0)
```

**Hacer lo mismo para forward():**
```python
def forward(
    self,
    user_message: str,
    context: DialogueContext,
    history: list[dict[str, str]] | None = None,
) -> NLUOutput:
    from soni.du.base import safe_extract_result

    result = self.extractor(
        user_message=user_message,
        context=context,
        history=history or [],
    )

    return safe_extract_result(
        result.result,
        NLUOutput,
        default_factory=lambda: NLUOutput(commands=[], confidence=0.0),
        context="NLU forward pass",
    )
```

#### Paso 3: Actualizar slot_extractor.py

**Archivo a modificar:** `src/soni/du/slot_extractor.py`

**Actualizar acall():**
```python
async def acall(
    self,
    user_message: str,
    slot_definitions: list[SlotExtractionInput],
) -> list[SetSlot]:
    from soni.du.base import safe_extract_result

    try:
        result = await self.extractor.acall(
            user_message=user_message,
            slots=slot_definitions,
        )

        extraction_result = safe_extract_result(
            result.result,
            SlotExtractionResult,
            default_factory=lambda: SlotExtractionResult(extracted_slots=[]),
            context="Slot extraction",
        )

        # Convert to SetSlot commands
        return [
            SetSlot(slot=slot.slot_name, value=slot.value)
            for slot in extraction_result.extracted_slots
            if slot.value is not None
        ]

    except Exception as e:
        logger.error(f"Slot extraction failed: {e}", exc_info=True)
        return []
```

**Actualizar forward():**
```python
def forward(
    self,
    user_message: str,
    slot_definitions: list[SlotExtractionInput],
) -> SlotExtractionResult:
    from soni.du.base import safe_extract_result

    result = self.extractor(
        user_message=user_message,
        slots=slot_definitions,
    )

    return safe_extract_result(
        result.result,
        SlotExtractionResult,
        default_factory=lambda: SlotExtractionResult(extracted_slots=[]),
        context="Slot extraction forward pass",
    )
```

### TDD Cycle (MANDATORY)

#### Red Phase: Write Failing Tests

**Test file:** `tests/unit/du/test_result_validation.py`

```python
"""Tests for DSPy result validation."""

import pytest
from unittest.mock import Mock
from pydantic import BaseModel, ValidationError

from soni.du.base import validate_dspy_result, safe_extract_result
from soni.du.models import NLUOutput, SlotExtractionResult


class SimpleModel(BaseModel):
    """Simple model for testing."""
    name: str
    value: int


class TestValidateDspyResult:
    """Test validate_dspy_result function."""

    def test_returns_instance_if_already_correct_type(self):
        """Should return as-is if already expected type."""
        expected = SimpleModel(name="test", value=42)

        result = validate_dspy_result(expected, SimpleModel)

        assert result is expected

    def test_validates_dict_input(self):
        """Should validate dict and convert to model."""
        data = {"name": "test", "value": 42}

        result = validate_dspy_result(data, SimpleModel)

        assert isinstance(result, SimpleModel)
        assert result.name == "test"
        assert result.value == 42

    def test_raises_on_none(self):
        """Should raise TypeError on None input."""
        with pytest.raises(TypeError) as exc_info:
            validate_dspy_result(None, SimpleModel)

        assert "None" in str(exc_info.value)

    def test_raises_on_invalid_dict(self):
        """Should raise ValidationError on invalid dict."""
        data = {"name": "test"}  # Missing required 'value'

        with pytest.raises(ValidationError):
            validate_dspy_result(data, SimpleModel)

    def test_extracts_from_store_attribute(self):
        """Should extract from _store if present (DSPy pattern)."""
        mock_result = Mock()
        mock_result._store = {"name": "from_store", "value": 100}

        result = validate_dspy_result(mock_result, SimpleModel)

        assert result.name == "from_store"
        assert result.value == 100

    def test_extracts_from_model_dump(self):
        """Should use model_dump if available."""
        mock_result = Mock()
        mock_result.model_dump = Mock(return_value={"name": "dumped", "value": 200})
        # Remove _store to force model_dump path
        del mock_result._store

        result = validate_dspy_result(mock_result, SimpleModel)

        assert result.name == "dumped"

    def test_raises_on_incompatible_type(self):
        """Should raise TypeError on incompatible input."""
        with pytest.raises(TypeError):
            validate_dspy_result("not a valid input", SimpleModel)


class TestSafeExtractResult:
    """Test safe_extract_result with fallback."""

    def test_returns_validated_result_on_success(self):
        """Should return validated result when valid."""
        data = {"name": "test", "value": 42}

        result = safe_extract_result(
            data,
            SimpleModel,
            default_factory=lambda: SimpleModel(name="default", value=0),
        )

        assert result.name == "test"
        assert result.value == 42

    def test_returns_default_on_none(self):
        """Should return default when result is None."""
        result = safe_extract_result(
            None,
            SimpleModel,
            default_factory=lambda: SimpleModel(name="default", value=0),
        )

        assert result.name == "default"
        assert result.value == 0

    def test_returns_default_on_validation_error(self):
        """Should return default when validation fails."""
        invalid_data = {"name": 123}  # Wrong type

        result = safe_extract_result(
            invalid_data,
            SimpleModel,
            default_factory=lambda: SimpleModel(name="fallback", value=-1),
        )

        assert result.name == "fallback"
        assert result.value == -1


class TestNLUOutputValidation:
    """Test validation with actual NLU types."""

    def test_validates_nlu_output_dict(self):
        """Should validate NLUOutput from dict."""
        data = {
            "commands": [],
            "confidence": 0.95,
        }

        result = validate_dspy_result(data, NLUOutput)

        assert isinstance(result, NLUOutput)
        assert result.confidence == 0.95

    def test_nlu_output_with_commands(self):
        """Should handle NLUOutput with command data."""
        data = {
            "commands": [
                {"type": "start_flow", "flow_name": "test_flow"}
            ],
            "confidence": 0.9,
        }

        result = validate_dspy_result(data, NLUOutput)

        assert len(result.commands) == 1


class TestSlotExtractionValidation:
    """Test validation with SlotExtractionResult."""

    def test_validates_slot_extraction_result(self):
        """Should validate SlotExtractionResult."""
        data = {
            "extracted_slots": [
                {"slot_name": "city", "value": "Paris", "confidence": 0.9}
            ]
        }

        result = validate_dspy_result(data, SlotExtractionResult)

        assert len(result.extracted_slots) == 1
        assert result.extracted_slots[0].slot_name == "city"
```

#### Green Phase

```bash
uv run pytest tests/unit/du/test_result_validation.py -v
```

### Criterios de Éxito

- [ ] No hay `cast()` sin validación en du/modules.py
- [ ] No hay `cast()` sin validación en du/slot_extractor.py
- [ ] `validate_dspy_result()` maneja todos los formatos de DSPy
- [ ] `safe_extract_result()` proporciona fallback seguro
- [ ] Logging útil cuando validación falla
- [ ] Tests de validación pasan

### Validación Manual

```bash
# Run DU tests
uv run pytest tests/unit/du/ -v

# Search for remaining cast() usage
grep -n "cast(" src/soni/du/*.py
# Should only show properly validated uses

# Test with actual DSPy (if configured)
uv run python -c "
from soni.du.modules import SoniDU
from soni.du.models import DialogueContext

du = SoniDU(use_cot=False)
# This should either succeed or fail with clear error, not silent corruption
"
```

### Referencias

- DSPy Prediction class: `ref/dspy/dspy/primitives/prediction.py`
- Pydantic validation: https://docs.pydantic.dev/latest/concepts/validation/
- Análisis original: DU modules cast() issues

### Notas Adicionales

- `safe_extract_result()` usa default_factory para permitir defaults dinámicos
- El logging ayuda a debuggear issues de formato DSPy en producción
- Considerar agregar métricas de tasa de fallback para monitoreo
- Si DSPy cambia su formato de respuesta, solo hay que actualizar `validate_dspy_result()`
