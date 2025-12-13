## Task: 3.4 - NLU Provider Implementation

**ID de tarea:** 304
**Hito:** Phase 3 - NLU System with DSPy
**Dependencias:** Task 303 (SoniDU Module)
**Duración estimada:** 1-2 horas

### Objetivo

Create concrete NLU provider implementing `INLUProvider` interface, bridging the gap between the runtime interface (dict-based) and the structured SoniDU module.

### Contexto

The `INLUProvider` interface expects dict-based inputs/outputs for runtime compatibility, while `SoniDU` uses structured Pydantic models. This provider converts between these formats, allowing the runtime to use the structured NLU system.

**Reference:** [docs/implementation/03-phase-3-nlu.md](../../docs/implementation/03-phase-3-nlu.md) - Task 3.4

### Entregables

- [ ] `DSPyNLUProvider` class created implementing `INLUProvider`
- [ ] Converts dict context to `DialogueContext` Pydantic model
- [ ] Converts list history to `dspy.History`
- [ ] Calls `SoniDU.predict()` with structured types
- [ ] Returns serialized `NLUOutput` as dict
- [ ] Tests passing with DummyLM
- [ ] Interface compliance verified

### Implementación Detallada

#### Paso 1: Create provider.py File

**Archivo(s) a crear/modificar:** `src/soni/du/provider.py`

**Código específico:**

```python
"""NLU provider implementation using DSPy SoniDU module."""

from typing import Any

import dspy

from soni.core.interfaces import INLUProvider
from soni.du.models import DialogueContext, NLUOutput
from soni.du.modules import SoniDU


class DSPyNLUProvider(INLUProvider):
    """NLU provider using DSPy SoniDU module."""

    def __init__(self, module: SoniDU) -> None:
        """Initialize provider with SoniDU module.

        Args:
            module: Optimized SoniDU module
        """
        self.module = module

    async def understand(
        self,
        user_message: str,
        dialogue_context: dict[str, Any],
    ) -> dict[str, Any]:
        """Understand user message and return NLU result.

        Args:
            user_message: User's input
            dialogue_context: Context dict with fields:
                - current_slots: dict
                - available_actions: list[str]
                - available_flows: list[str]
                - current_flow: str
                - expected_slots: list[str]
                - history: list[dict] (optional)

        Returns:
            Serialized NLUOutput as dict
        """
        # Build structured context
        context = DialogueContext(
            current_slots=dialogue_context.get("current_slots", {}),
            available_actions=dialogue_context.get("available_actions", []),
            available_flows=dialogue_context.get("available_flows", []),
            current_flow=dialogue_context.get("current_flow", "none"),
            expected_slots=dialogue_context.get("expected_slots", []),
        )

        # Build history
        history_data = dialogue_context.get("history", [])
        history = dspy.History(messages=history_data)

        # Call NLU
        result: NLUOutput = await self.module.predict(
            user_message=user_message,
            history=history,
            context=context,
        )

        # Return serialized
        return result.model_dump()
```

**Explicación:**
- Create new file `src/soni/du/provider.py`
- Implement `INLUProvider` interface
- Convert dict-based `dialogue_context` to `DialogueContext` Pydantic model
- Convert list-based `history` to `dspy.History`
- Call `SoniDU.predict()` with structured types
- Return `NLUOutput.model_dump()` to serialize to dict
- Handle missing fields with defaults

#### Paso 2: Create Unit Tests

**Archivo(s) a crear/modificar:** `tests/unit/test_nlu_provider.py`

**Código específico:**

```python
import pytest
import dspy
from dspy.utils.dummies import DummyLM
from soni.du.provider import DSPyNLUProvider
from soni.du.modules import SoniDU

@pytest.fixture
def dummy_lm():
    """Create DummyLM for testing."""
    lm = DummyLM([
        {
            "result": {
                "message_type": "interruption",
                "command": "book_flight",
                "slots": [],
                "confidence": 0.95,
                "reasoning": "User explicitly states intent"
            }
        }
    ])
    dspy.configure(lm=lm)
    return lm

@pytest.mark.asyncio
async def test_dspy_nlu_provider(dummy_lm):
    """Test DSPyNLUProvider with DummyLM."""
    # Arrange
    module = SoniDU()
    provider = DSPyNLUProvider(module)

    dialogue_context = {
        "current_slots": {},
        "available_actions": ["book_flight"],
        "available_flows": ["book_flight"],
        "current_flow": "none",
        "expected_slots": [],
        "history": []
    }

    # Act
    result = await provider.understand("book a flight", dialogue_context)

    # Assert
    assert result["command"] == "book_flight"
    assert result["message_type"] == "interruption"
```

**Explicación:**
- Create test file with AAA pattern
- Use DummyLM for testing
- Test provider with dict-based context
- Verify output is dict with expected fields
- All tests must have clear docstrings

### Tests Requeridos

**Archivo de tests:** `tests/unit/test_nlu_provider.py`

**Tests específicos a implementar:**

```python
import pytest
import dspy
from dspy.utils.dummies import DummyLM
from soni.du.provider import DSPyNLUProvider
from soni.du.modules import SoniDU

@pytest.fixture
def dummy_lm():
    """Create DummyLM for testing."""
    lm = DummyLM([
        {
            "result": {
                "message_type": "interruption",
                "command": "book_flight",
                "slots": [],
                "confidence": 0.95,
                "reasoning": "User explicitly states intent"
            }
        }
    ])
    dspy.configure(lm=lm)
    return lm

@pytest.mark.asyncio
async def test_dspy_nlu_provider(dummy_lm):
    """Test DSPyNLUProvider with DummyLM."""
    # Arrange
    module = SoniDU()
    provider = DSPyNLUProvider(module)

    dialogue_context = {
        "current_slots": {},
        "available_actions": ["book_flight"],
        "available_flows": ["book_flight"],
        "current_flow": "none",
        "expected_slots": [],
        "history": []
    }

    # Act
    result = await provider.understand("book a flight", dialogue_context)

    # Assert
    assert result["command"] == "book_flight"
    assert result["message_type"] == "interruption"
    assert "confidence" in result
    assert "reasoning" in result
    assert "slots" in result

@pytest.mark.asyncio
async def test_dspy_nlu_provider_with_history(dummy_lm):
    """Test DSPyNLUProvider with conversation history."""
    # Arrange
    module = SoniDU()
    provider = DSPyNLUProvider(module)

    dialogue_context = {
        "current_slots": {"origin": "Madrid"},
        "available_actions": ["book_flight"],
        "available_flows": ["book_flight"],
        "current_flow": "book_flight",
        "expected_slots": ["destination"],
        "history": [
            {"role": "user", "content": "I want to book a flight"},
            {"role": "assistant", "content": "Where are you departing from?"}
        ]
    }

    # Act
    result = await provider.understand("Barcelona", dialogue_context)

    # Assert
    assert result["command"] == "book_flight"
    assert "slots" in result

@pytest.mark.asyncio
async def test_dspy_nlu_provider_missing_fields(dummy_lm):
    """Test DSPyNLUProvider handles missing context fields."""
    # Arrange
    module = SoniDU()
    provider = DSPyNLUProvider(module)

    dialogue_context = {}  # Empty context

    # Act
    result = await provider.understand("test", dialogue_context)

    # Assert
    assert result is not None
    assert "command" in result
    assert result.get("current_flow", "none") == "none"  # Default value
```

### Criterios de Éxito

- [ ] Provider implemented
- [ ] Interface compliance verified (implements `INLUProvider`)
- [ ] Tests passing (`uv run pytest tests/unit/test_nlu_provider.py -v`)
- [ ] Mypy passes (`uv run mypy src/soni/du/provider.py`)
- [ ] Ruff passes (`uv run ruff check src/soni/du/provider.py`)

### Validación Manual

**Comandos para validar:**

```bash
# Type checking
uv run mypy src/soni/du/provider.py

# Tests
uv run pytest tests/unit/test_nlu_provider.py -v

# Linting
uv run ruff check src/soni/du/provider.py
uv run ruff format src/soni/du/provider.py

# Verify interface compliance
uv run python -c "from soni.du.provider import DSPyNLUProvider; from soni.core.interfaces import INLUProvider; assert issubclass(DSPyNLUProvider, type(INLUProvider))"
```

**Resultado esperado:**
- Mypy shows no errors
- All tests pass
- Ruff shows no linting errors
- Provider can be imported and used correctly
- Interface compliance verified

### Referencias

- [docs/implementation/03-phase-3-nlu.md](../../docs/implementation/03-phase-3-nlu.md) - Task 3.4
- [src/soni/core/interfaces.py](../../src/soni/core/interfaces.py) - INLUProvider interface

### Notas Adicionales

- Provider bridges dict-based runtime interface with structured NLU module
- Handles missing context fields with defaults
- Returns serialized `NLUOutput` as dict for runtime compatibility
- History is converted from list[dict] to `dspy.History`
- This provider will be used by understand_node in Phase 4
