## Task: 002 - Add Error Handling in SoniDU.aforward()

**ID de tarea:** 002
**Hito:** Robustness
**Dependencias:** Ninguna
**Duración estimada:** 1.5 horas

### Objetivo

Añadir manejo de errores en `SoniDU.aforward()` para prevenir fallos en cascada cuando DSPy/LLM falla.

### Contexto

Actualmente `du/modules.py:aforward()` no tiene try/except:

```python
async def aforward(...) -> NLUOutput:
    result = await self.extractor.acall(...)
    return result.result  # Si falla, cascadea
```

Si el LLM falla (rate limit, timeout, parse error), el error propaga sin control hasta el usuario.

### Entregables

- [ ] Wrap `acall()` en try/except
- [ ] Retornar `NLUOutput` vacío con `confidence=0.0` en caso de error
- [ ] Logging del error para observabilidad
- [ ] Tests unitarios para casos de error

### Implementación Detallada

#### Paso 1: Añadir error handling

**Archivo(s) a modificar:** `src/soni/du/modules.py`

```python
async def aforward(
    self,
    user_message: str,
    context: DialogueContext,
    history: list[dict[str, str]] | None = None,
) -> NLUOutput:
    """Extract commands from user message (async)."""
    history_obj = dspy.History(messages=history or [])

    try:
        result = await self.extractor.acall(
            user_message=user_message,
            context=context,
            history=history_obj,
        )
        return result.result
    except Exception as e:
        logger.error(f"NLU extraction failed: {e}", exc_info=True)
        # Return safe fallback - no commands, zero confidence
        return NLUOutput(commands=[], confidence=0.0)
```

### TDD Cycle (MANDATORY)

#### Red Phase: Write Failing Tests

**Test file:** `tests/unit/du/test_modules_error_handling.py`

```python
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from soni.du.modules import SoniDU
from soni.du.models import DialogueContext, NLUOutput


@pytest.fixture
def mock_context():
    """Create minimal DialogueContext for testing."""
    return DialogueContext(
        available_flows=[],
        available_commands=[],
        active_flow=None,
        current_slots=[],
        expected_slot=None,
    )


class TestSoniDUErrorHandling:
    """Tests for SoniDU error handling."""

    @pytest.mark.asyncio
    async def test_aforward_returns_empty_on_extractor_error(self, mock_context):
        """Test that NLU errors return empty output, not raise."""
        # Arrange
        du = SoniDU(use_cot=False)
        du.extractor = MagicMock()
        du.extractor.acall = AsyncMock(side_effect=RuntimeError("LLM timeout"))

        # Act
        result = await du.aforward("hello", mock_context)

        # Assert
        assert isinstance(result, NLUOutput)
        assert result.commands == []
        assert result.confidence == 0.0

    @pytest.mark.asyncio
    async def test_aforward_logs_error_on_failure(self, mock_context, caplog):
        """Test that errors are logged for observability."""
        # Arrange
        import logging
        caplog.set_level(logging.ERROR)

        du = SoniDU(use_cot=False)
        du.extractor = MagicMock()
        du.extractor.acall = AsyncMock(side_effect=ValueError("Parse error"))

        # Act
        await du.aforward("hello", mock_context)

        # Assert
        assert "NLU extraction failed" in caplog.text
        assert "Parse error" in caplog.text

    @pytest.mark.asyncio
    async def test_aforward_success_still_works(self, mock_context):
        """Test that normal operation is unaffected."""
        # Arrange
        du = SoniDU(use_cot=False)
        expected_output = NLUOutput(commands=[], confidence=0.9)

        mock_result = MagicMock()
        mock_result.result = expected_output

        du.extractor = MagicMock()
        du.extractor.acall = AsyncMock(return_value=mock_result)

        # Act
        result = await du.aforward("hello", mock_context)

        # Assert
        assert result == expected_output
        assert result.confidence == 0.9
```

**Verify tests fail:**
```bash
uv run pytest tests/unit/du/test_modules_error_handling.py -v
# Expected: FAILED (no error handling yet)
```

#### Green Phase: Make Tests Pass

Implementar el try/except en `aforward()`.

```bash
uv run pytest tests/unit/du/test_modules_error_handling.py -v
# Expected: PASSED ✅
```

### Criterios de Éxito

- [ ] `aforward()` nunca propaga excepciones de DSPy
- [ ] En error, retorna `NLUOutput(commands=[], confidence=0.0)`
- [ ] Errores se loguean con nivel ERROR
- [ ] `uv run pytest` pasa
- [ ] `uv run ruff check .` sin errores
- [ ] `uv run mypy src/soni` sin errores

### Validación Manual

```bash
uv run pytest tests/unit/du/ -v
uv run ruff check src/soni/du/
uv run mypy src/soni/du/
```

### Referencias

- `src/soni/du/modules.py:78-99` - Método aforward actual
