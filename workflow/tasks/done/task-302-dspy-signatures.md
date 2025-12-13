## Task: 3.2 - DSPy Signatures

**ID de tarea:** 302
**Hito:** Phase 3 - NLU System with DSPy
**Dependencias:** Task 301 (Pydantic Models)
**Duración estimada:** 1-2 horas

### Objetivo

Refactor DSPy signatures to use structured Pydantic models instead of string-based inputs, providing type safety and validation throughout the NLU pipeline.

### Contexto

This task refactors the existing `DialogueUnderstanding` signature to use Pydantic models (`DialogueContext`, `NLUOutput`) and `dspy.History` for proper conversation history management. This replaces the current string-based approach with structured types.

**Reference:** [docs/implementation/03-phase-3-nlu.md](../../docs/implementation/03-phase-3-nlu.md) - Task 3.2

### Entregables

- [ ] `DialogueUnderstanding` signature refactored to use `DialogueContext` Pydantic model
- [ ] Signature uses `dspy.History` for conversation history
- [ ] Output field uses `NLUOutput` Pydantic model
- [ ] All fields properly documented
- [ ] Tests passing in `tests/unit/test_nlu_signatures.py`
- [ ] Mypy passes without errors

### Implementación Detallada

#### Paso 1: Refactor signatures.py

**Archivo(s) a crear/modificar:** `src/soni/du/signatures.py`

**Código específico:**

```python
"""DSPy signatures for Dialogue Understanding."""

import dspy
from soni.du.models import NLUOutput, DialogueContext


class DialogueUnderstanding(dspy.Signature):
    """Extract user intent and entities with structured types.

    Uses Pydantic models for robust type safety and validation.
    Uses dspy.History for proper conversation history management.
    """

    # Input fields with structured types
    user_message: str = dspy.InputField(
        desc="The user's current message"
    )
    history: dspy.History = dspy.InputField(
        desc="Conversation history with user messages and assistant responses"
    )
    context: DialogueContext = dspy.InputField(
        desc="Current dialogue context with all relevant information"
    )
    current_datetime: str = dspy.InputField(
        desc="Current datetime in ISO format for relative date resolution",
        default=""
    )

    # Output field with structured type
    result: NLUOutput = dspy.OutputField(
        desc="Complete NLU analysis with type-safe structure"
    )
```

**Explicación:**
- Replace string-based inputs with `DialogueContext` Pydantic model
- Use `dspy.History` for conversation history (replaces `dialogue_history` string)
- Output field uses `NLUOutput` Pydantic model (replaces multiple string outputs)
- Remove old string-based fields (`dialogue_history`, `current_slots`, `available_actions`, etc.)
- Keep `user_message` and `current_datetime` as strings (they are simple values)

#### Paso 2: Create Unit Tests

**Archivo(s) a crear/modificar:** `tests/unit/test_nlu_signatures.py`

**Código específico:**

```python
import pytest
import dspy
from soni.du.signatures import DialogueUnderstanding
from soni.du.models import DialogueContext

def test_signature_has_required_fields():
    """Test signature has all required input/output fields."""
    # Arrange
    sig = DialogueUnderstanding

    # Act
    input_fields = list(sig.input_fields.keys())
    output_fields = list(sig.output_fields.keys())

    # Assert
    assert "user_message" in input_fields
    assert "history" in input_fields
    assert "context" in input_fields
    assert "current_datetime" in input_fields
    assert "result" in output_fields
```

**Explicación:**
- Create test file with AAA pattern
- Test signature structure (input/output fields)
- Verify all required fields are present
- All tests must have clear docstrings

### Tests Requeridos

**Archivo de tests:** `tests/unit/test_nlu_signatures.py`

**Tests específicos a implementar:**

```python
import pytest
import dspy
from soni.du.signatures import DialogueUnderstanding
from soni.du.models import DialogueContext

def test_signature_has_required_fields():
    """Test signature has all required input/output fields."""
    # Arrange
    sig = DialogueUnderstanding

    # Act
    input_fields = list(sig.input_fields.keys())
    output_fields = list(sig.output_fields.keys())

    # Assert
    assert "user_message" in input_fields
    assert "history" in input_fields
    assert "context" in input_fields
    assert "current_datetime" in input_fields
    assert "result" in output_fields

def test_signature_uses_structured_types():
    """Test signature uses Pydantic models for structured types."""
    # Arrange
    sig = DialogueUnderstanding

    # Act
    context_field = sig.input_fields.get("context")
    result_field = sig.output_fields.get("result")

    # Assert
    assert context_field is not None
    assert result_field is not None
    # Verify types are DialogueContext and NLUOutput (check annotations)
    assert hasattr(context_field, "annotation")
    assert hasattr(result_field, "annotation")

def test_signature_has_history_field():
    """Test signature uses dspy.History for conversation history."""
    # Arrange
    sig = DialogueUnderstanding

    # Act
    history_field = sig.input_fields.get("history")

    # Assert
    assert history_field is not None
    assert "history" in sig.input_fields
```

### Criterios de Éxito

- [ ] Signature refactored to use Pydantic models
- [ ] All fields documented
- [ ] Tests passing (`uv run pytest tests/unit/test_nlu_signatures.py -v`)
- [ ] Mypy passes (`uv run mypy src/soni/du/signatures.py`)
- [ ] Ruff passes (`uv run ruff check src/soni/du/signatures.py`)
- [ ] Old string-based fields removed

### Validación Manual

**Comandos para validar:**

```bash
# Type checking
uv run mypy src/soni/du/signatures.py

# Tests
uv run pytest tests/unit/test_nlu_signatures.py -v

# Linting
uv run ruff check src/soni/du/signatures.py
uv run ruff format src/soni/du/signatures.py
```

**Resultado esperado:**
- Mypy shows no errors
- All tests pass
- Ruff shows no linting errors
- Signature can be imported and used correctly

### Referencias

- [docs/implementation/03-phase-3-nlu.md](../../docs/implementation/03-phase-3-nlu.md) - Task 3.2
- [docs/design/09-dspy-optimization.md](../../docs/design/09-dspy-optimization.md) - Structured types design
- [DSPy documentation](https://dspy-docs.vercel.app/)

### Notas Adicionales

- This is a refactoring task - old string-based signature must be completely replaced
- The new signature uses structured types throughout
- `dspy.History` is the proper way to handle conversation history in DSPy
- This change will require updates to modules.py (Task 303)
- Verify no other files import the old signature format
