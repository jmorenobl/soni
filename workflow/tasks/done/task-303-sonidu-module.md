## Task: 3.3 - SoniDU Module

**ID de tarea:** 303
**Hito:** Phase 3 - NLU System with DSPy
**Dependencias:** Task 301 (Pydantic Models), Task 302 (DSPy Signatures)
**Duración estimada:** 3-4 horas

### Objetivo

Refactor SoniDU module to use structured Pydantic models and `dspy.History`, replacing string-based inputs and the `NLUResult` dataclass with `NLUOutput` Pydantic model.

### Contexto

This is a significant refactoring task. The existing `SoniDU` module uses string-based inputs and a `NLUResult` dataclass. This task updates it to use structured types (`DialogueContext`, `dspy.History`, `NLUOutput`) throughout, providing type safety and eliminating parsing logic.

**Reference:** [docs/implementation/03-phase-3-nlu.md](../../docs/implementation/03-phase-3-nlu.md) - Task 3.3

### Entregables

- [ ] `SoniDU` module refactored to use `DialogueContext` and `dspy.History`
- [ ] `forward()` and `aforward()` methods updated to use structured types
- [ ] `predict()` method returns `NLUOutput` instead of `NLUResult`
- [ ] `NLUResult` dataclass removed
- [ ] Cache updated to store `NLUOutput` instead of `NLUResult`
- [ ] `_get_cache_key()` updated to work with structured types
- [ ] Tests passing with DummyLM
- [ ] All usages of old interface updated

### Implementación Detallada

#### Paso 1: Refactor modules.py

**Archivo(s) a crear/modificar:** `src/soni/du/modules.py`

**Código específico:**

```python
"""DSPy modules for Dialogue Understanding."""

import dspy
from soni.du.signatures import DialogueUnderstanding
from soni.du.models import NLUOutput, DialogueContext
from cachetools import TTLCache

class SoniDU(dspy.Module):
    """
    Soni Dialogue Understanding module with structured types.

    This module provides:
    - Type-safe async interface for runtime
    - Sync interface for DSPy optimizers
    - Automatic prompt optimization via DSPy
    - Structured Pydantic models throughout
    """

    def __init__(self, cache_size: int = 1000, cache_ttl: int = 300) -> None:
        """Initialize SoniDU module.

        Args:
            cache_size: Maximum number of cached NLU results
            cache_ttl: Time-to-live for cache entries in seconds
        """
        super().__init__()  # CRITICAL: Must call super().__init__()

        # Create predictor with structured signature
        self.predictor = dspy.ChainOfThought(DialogueUnderstanding)

        # Optional caching layer
        self.nlu_cache: TTLCache[str, NLUOutput] = TTLCache(
            maxsize=cache_size,
            ttl=cache_ttl
        )

    def forward(
        self,
        user_message: str,
        history: dspy.History,
        context: DialogueContext,
        current_datetime: str = "",
    ) -> dspy.Prediction:
        """Sync forward pass for DSPy optimizers.

        Used during optimization/training with MIPROv2, BootstrapFewShot, etc.

        Args:
            user_message: User's input message
            history: Conversation history (dspy.History)
            context: Dialogue context with slots, actions, flows (DialogueContext)
            current_datetime: Current datetime in ISO format

        Returns:
            dspy.Prediction object with result field containing NLUOutput
        """
        return self.predictor(
            user_message=user_message,
            history=history,
            context=context,
            current_datetime=current_datetime,
        )

    async def aforward(
        self,
        user_message: str,
        history: dspy.History,
        context: DialogueContext,
        current_datetime: str = "",
    ) -> dspy.Prediction:
        """Async forward pass for production runtime.

        Called internally by acall(). Uses async LM calls via DSPy's adapter system.

        Args:
            Same as forward()

        Returns:
            dspy.Prediction object with result field containing NLUOutput
        """
        # DSPy's predictor.acall() handles async LM calls
        return await self.predictor.acall(
            user_message=user_message,
            history=history,
            context=context,
            current_datetime=current_datetime,
        )

    async def predict(
        self,
        user_message: str,
        history: dspy.History,
        context: DialogueContext,
    ) -> NLUOutput:
        """High-level async prediction method with caching.

        This is the main entry point for runtime NLU calls. Provides:
        - Structured type inputs (dspy.History, DialogueContext)
        - NLUOutput Pydantic model output
        - Automatic caching
        - Internal datetime management

        Args:
            user_message: User's input message
            history: Conversation history (dspy.History)
            context: Dialogue context (DialogueContext)

        Returns:
            NLUOutput with message_type, command, slots, confidence, and reasoning
        """
        from datetime import datetime

        # Calculate current datetime (encapsulation principle)
        current_datetime_str = datetime.now().isoformat()

        # Check cache
        cache_key = self._get_cache_key(user_message, history, context)

        if cache_key in self.nlu_cache:
            return self.nlu_cache[cache_key]

        # Call via acall() (public async method)
        prediction = await self.acall(
            user_message=user_message,
            history=history,
            context=context,
            current_datetime=current_datetime_str,
        )

        # Extract structured result (no parsing needed!)
        result: NLUOutput = prediction.result

        # Cache and return
        self.nlu_cache[cache_key] = result

        return result

    def _get_cache_key(
        self,
        user_message: str,
        history: dspy.History,
        context: DialogueContext,
    ) -> str:
        """Generate cache key from structured inputs."""
        import hashlib
        import json

        data = {
            "message": user_message,
            "history_length": len(history.messages),
            "context": context.model_dump(),
        }

        json_str = json.dumps(data, sort_keys=True)
        return hashlib.sha256(json_str.encode()).hexdigest()
```

**Explicación:**
- Remove `NLUResult` dataclass completely
- Update `forward()` and `aforward()` to use `DialogueContext` and `dspy.History`
- Update `predict()` to return `NLUOutput` instead of `NLUResult`
- Update cache type from `TTLCache[str, NLUResult]` to `TTLCache[str, NLUOutput]`
- Update `_get_cache_key()` to work with structured types
- Remove all JSON parsing logic (no longer needed with structured types)
- Remove old string-based parameter handling

#### Paso 2: Create/Update Unit Tests

**Archivo(s) a crear/modificar:** `tests/unit/test_nlu_module.py`

**Código específico:**

```python
import pytest
import dspy
from dspy.utils.dummies import DummyLM
from soni.du.modules import SoniDU
from soni.du.models import DialogueContext, MessageType, NLUOutput

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
async def test_soni_du_predict(dummy_lm):
    """Test SoniDU.predict with DummyLM."""
    # Arrange
    module = SoniDU()
    user_message = "I want to book a flight"
    history = dspy.History(messages=[])
    context = DialogueContext(
        current_slots={},
        available_actions=["book_flight"],
        available_flows=["book_flight"],
        current_flow="none",
        expected_slots=[]
    )

    # Act
    result = await module.predict(user_message, history, context)

    # Assert
    assert isinstance(result, NLUOutput)
    assert result.command == "book_flight"
    assert result.message_type == MessageType.INTERRUPTION
    assert result.confidence > 0.7

@pytest.mark.asyncio
async def test_soni_du_caching(dummy_lm):
    """Test SoniDU caches results."""
    # Arrange
    module = SoniDU()
    user_message = "test"
    history = dspy.History(messages=[])
    context = DialogueContext()

    # Act
    result1 = await module.predict(user_message, history, context)
    result2 = await module.predict(user_message, history, context)

    # Assert - Should be same object (cached)
    assert result1 is result2
```

**Explicación:**
- Create/update test file with AAA pattern
- Use DummyLM for testing (no real LLM calls)
- Test `predict()` method with structured inputs
- Test caching functionality
- All tests must have clear docstrings

### Tests Requeridos

**Archivo de tests:** `tests/unit/test_nlu_module.py`

**Tests específicos a implementar:**

```python
import pytest
import dspy
from dspy.utils.dummies import DummyLM
from soni.du.modules import SoniDU
from soni.du.models import DialogueContext, MessageType, NLUOutput

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
async def test_soni_du_predict(dummy_lm):
    """Test SoniDU.predict with DummyLM."""
    # Arrange
    module = SoniDU()
    user_message = "I want to book a flight"
    history = dspy.History(messages=[])
    context = DialogueContext(
        current_slots={},
        available_actions=["book_flight"],
        available_flows=["book_flight"],
        current_flow="none",
        expected_slots=[]
    )

    # Act
    result = await module.predict(user_message, history, context)

    # Assert
    assert isinstance(result, NLUOutput)
    assert result.command == "book_flight"
    assert result.message_type == MessageType.INTERRUPTION
    assert result.confidence > 0.7

@pytest.mark.asyncio
async def test_soni_du_caching(dummy_lm):
    """Test SoniDU caches results."""
    # Arrange
    module = SoniDU()
    user_message = "test"
    history = dspy.History(messages=[])
    context = DialogueContext()

    # Act
    result1 = await module.predict(user_message, history, context)
    result2 = await module.predict(user_message, history, context)

    # Assert - Should be same object (cached)
    assert result1 is result2

def test_soni_du_forward_sync(dummy_lm):
    """Test SoniDU.forward sync method."""
    # Arrange
    module = SoniDU()
    user_message = "test"
    history = dspy.History(messages=[])
    context = DialogueContext()

    # Act
    prediction = module.forward(user_message, history, context)

    # Assert
    assert hasattr(prediction, "result")
    assert isinstance(prediction.result, dict)  # DummyLM returns dict

@pytest.mark.asyncio
async def test_soni_du_aforward_async(dummy_lm):
    """Test SoniDU.aforward async method."""
    # Arrange
    module = SoniDU()
    user_message = "test"
    history = dspy.History(messages=[])
    context = DialogueContext()

    # Act
    prediction = await module.aforward(user_message, history, context)

    # Assert
    assert hasattr(prediction, "result")
```

### Criterios de Éxito

- [ ] Module refactored to use structured types
- [ ] `NLUResult` dataclass removed
- [ ] Async/sync methods working
- [ ] Caching working with `NLUOutput`
- [ ] Tests passing with DummyLM
- [ ] Mypy passes (`uv run mypy src/soni/du/modules.py`)
- [ ] Ruff passes (`uv run ruff check src/soni/du/modules.py`)
- [ ] All usages of old interface updated (check optimizers.py, provider.py)

### Validación Manual

**Comandos para validar:**

```bash
# Type checking
uv run mypy src/soni/du/modules.py

# Tests
uv run pytest tests/unit/test_nlu_module.py -v

# Linting
uv run ruff check src/soni/du/modules.py
uv run ruff format src/soni/du/modules.py

# Check for old NLUResult usage
uv run grep -r "NLUResult" src/soni/
```

**Resultado esperado:**
- Mypy shows no errors
- All tests pass
- Ruff shows no linting errors
- No references to `NLUResult` remain in codebase
- Module can be imported and used correctly

### Referencias

- [docs/implementation/03-phase-3-nlu.md](../../docs/implementation/03-phase-3-nlu.md) - Task 3.3
- [docs/design/09-dspy-optimization.md](../../docs/design/09-dspy-optimization.md) - Structured types design
- [DSPy documentation](https://dspy-docs.vercel.app/)

### Notas Adicionales

- This is a significant refactoring - verify all usages are updated
- Check `src/soni/du/optimizers.py` for old interface usage
- Remove all JSON parsing logic (no longer needed)
- Cache now stores `NLUOutput` Pydantic models directly
- `_get_cache_key()` uses `context.model_dump()` for serialization
- Verify no other files import `NLUResult` dataclass
