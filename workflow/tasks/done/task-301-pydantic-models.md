## Task: 3.1 - Pydantic Models

**ID de tarea:** 301
**Hito:** Phase 3 - NLU System with DSPy
**Dependencias:** Ninguna
**Duración estimada:** 2-3 horas

### Objetivo

Define Pydantic models for NLU inputs and outputs to provide structured types with validation and type safety throughout the NLU system.

### Contexto

This is the foundational task for Phase 3. Pydantic models provide validation and type safety, replacing string-based inputs with structured types. All other NLU components will depend on these models.

**Reference:** [docs/implementation/03-phase-3-nlu.md](../../docs/implementation/03-phase-3-nlu.md) - Task 3.1

### Entregables

- [ ] `MessageType` enum defined with all message types
- [ ] `SlotValue` Pydantic model with name, value, and confidence
- [ ] `NLUOutput` Pydantic model with message_type, command, slots, confidence, and reasoning
- [ ] `DialogueContext` Pydantic model with all context fields
- [ ] Field validators working (confidence bounds 0.0-1.0)
- [ ] Tests passing in `tests/unit/test_nlu_models.py`
- [ ] Mypy passes without errors

### Implementación Detallada

#### Paso 1: Create models.py File

**Archivo(s) a crear/modificar:** `src/soni/du/models.py`

**Código específico:**

```python
from pydantic import BaseModel, Field
from enum import Enum
from typing import Any

class MessageType(str, Enum):
    """Type of user message."""
    SLOT_VALUE = "slot_value"           # Direct answer to current prompt
    CORRECTION = "correction"            # Fixing a previous value
    MODIFICATION = "modification"        # Requesting to change a slot
    INTERRUPTION = "interruption"        # New intent/flow
    DIGRESSION = "digression"            # Question without flow change
    CLARIFICATION = "clarification"      # Asking for explanation
    CANCELLATION = "cancellation"        # Wants to stop
    CONFIRMATION = "confirmation"        # Yes/no to confirm prompt
    CONTINUATION = "continuation"        # General continuation

class SlotValue(BaseModel):
    """Extracted slot value with metadata."""
    name: str = Field(description="Slot name (must match expected_slots)")
    value: Any = Field(description="Extracted value")
    confidence: float = Field(ge=0.0, le=1.0, description="Extraction confidence")

class NLUOutput(BaseModel):
    """Structured NLU output."""
    message_type: MessageType = Field(description="Type of user message")
    command: str = Field(description="User's intent/command")
    slots: list[SlotValue] = Field(default_factory=list, description="Extracted slot values")
    confidence: float = Field(ge=0.0, le=1.0, description="Overall confidence")
    reasoning: str = Field(description="Step-by-step reasoning")

class DialogueContext(BaseModel):
    """Current dialogue context for NLU."""
    current_slots: dict[str, Any] = Field(default_factory=dict, description="Filled slots")
    available_actions: list[str] = Field(default_factory=list, description="Available actions")
    available_flows: list[str] = Field(default_factory=list, description="Available flows")
    current_flow: str = Field(default="none", description="Active flow")
    expected_slots: list[str] = Field(default_factory=list, description="Expected slot names")
```

**Explicación:**
- Create the file with all Pydantic model definitions
- Use `MessageType` enum for type-safe message classification
- Use `Field` with validators for confidence bounds (0.0-1.0)
- Use `default_factory` for mutable defaults (lists, dicts)
- All models must have proper docstrings

#### Paso 2: Create Unit Tests

**Archivo(s) a crear/modificar:** `tests/unit/test_nlu_models.py`

**Código específico:**

```python
import pytest
from pydantic import ValidationError
from soni.du.models import NLUOutput, MessageType, SlotValue, DialogueContext

def test_nlu_output_valid():
    """Test NLUOutput with valid data."""
    # Arrange & Act
    output = NLUOutput(
        message_type=MessageType.INTERRUPTION,
        command="book_flight",
        slots=[],
        confidence=0.95,
        reasoning="User explicitly states booking intent"
    )

    # Assert
    assert output.command == "book_flight"
    assert output.confidence == 0.95

def test_nlu_output_confidence_validation():
    """Test NLUOutput validates confidence bounds."""
    # Arrange & Act & Assert
    with pytest.raises(ValidationError):
        NLUOutput(
            message_type=MessageType.INTERRUPTION,
            command="test",
            slots=[],
            confidence=1.5,  # Invalid: > 1.0
            reasoning="test"
        )

def test_slot_value_structure():
    """Test SlotValue with valid data."""
    # Arrange & Act
    slot = SlotValue(
        name="origin",
        value="Madrid",
        confidence=0.9
    )

    # Assert
    assert slot.name == "origin"
    assert slot.value == "Madrid"

def test_dialogue_context_defaults():
    """Test DialogueContext has proper defaults."""
    # Arrange & Act
    context = DialogueContext()

    # Assert
    assert context.current_flow == "none"
    assert len(context.available_actions) == 0
```

**Explicación:**
- Create test file with AAA pattern
- Test valid model creation
- Test validation errors (confidence bounds)
- Test default values
- All tests must have clear docstrings

### Tests Requeridos

**Archivo de tests:** `tests/unit/test_nlu_models.py`

**Tests específicos a implementar:**

```python
import pytest
from pydantic import ValidationError
from soni.du.models import NLUOutput, MessageType, SlotValue, DialogueContext

def test_nlu_output_valid():
    """Test NLUOutput with valid data."""
    # Arrange & Act
    output = NLUOutput(
        message_type=MessageType.INTERRUPTION,
        command="book_flight",
        slots=[],
        confidence=0.95,
        reasoning="User explicitly states booking intent"
    )

    # Assert
    assert output.command == "book_flight"
    assert output.confidence == 0.95
    assert output.message_type == MessageType.INTERRUPTION

def test_nlu_output_confidence_validation():
    """Test NLUOutput validates confidence bounds."""
    # Arrange & Act & Assert
    with pytest.raises(ValidationError):
        NLUOutput(
            message_type=MessageType.INTERRUPTION,
            command="test",
            slots=[],
            confidence=1.5,  # Invalid: > 1.0
            reasoning="test"
        )

def test_nlu_output_confidence_negative():
    """Test NLUOutput rejects negative confidence."""
    # Arrange & Act & Assert
    with pytest.raises(ValidationError):
        NLUOutput(
            message_type=MessageType.INTERRUPTION,
            command="test",
            slots=[],
            confidence=-0.1,  # Invalid: < 0.0
            reasoning="test"
        )

def test_slot_value_structure():
    """Test SlotValue with valid data."""
    # Arrange & Act
    slot = SlotValue(
        name="origin",
        value="Madrid",
        confidence=0.9
    )

    # Assert
    assert slot.name == "origin"
    assert slot.value == "Madrid"
    assert slot.confidence == 0.9

def test_slot_value_confidence_validation():
    """Test SlotValue validates confidence bounds."""
    # Arrange & Act & Assert
    with pytest.raises(ValidationError):
        SlotValue(
            name="origin",
            value="Madrid",
            confidence=1.5  # Invalid: > 1.0
        )

def test_dialogue_context_defaults():
    """Test DialogueContext has proper defaults."""
    # Arrange & Act
    context = DialogueContext()

    # Assert
    assert context.current_flow == "none"
    assert len(context.available_actions) == 0
    assert len(context.available_flows) == 0
    assert len(context.current_slots) == 0
    assert len(context.expected_slots) == 0

def test_dialogue_context_custom_values():
    """Test DialogueContext with custom values."""
    # Arrange & Act
    context = DialogueContext(
        current_flow="book_flight",
        available_actions=["book_flight", "search_flights"],
        current_slots={"origin": "Madrid"}
    )

    # Assert
    assert context.current_flow == "book_flight"
    assert len(context.available_actions) == 2
    assert context.current_slots["origin"] == "Madrid"

def test_message_type_enum():
    """Test MessageType enum values."""
    # Arrange & Act
    types = [
        MessageType.SLOT_VALUE,
        MessageType.CORRECTION,
        MessageType.MODIFICATION,
        MessageType.INTERRUPTION,
        MessageType.DIGRESSION,
        MessageType.CLARIFICATION,
        MessageType.CANCELLATION,
        MessageType.CONFIRMATION,
        MessageType.CONTINUATION,
    ]

    # Assert
    assert len(types) == 9
    assert MessageType.INTERRUPTION.value == "interruption"
```

### Criterios de Éxito

- [ ] All Pydantic models defined
- [ ] Field validators working (confidence bounds)
- [ ] Tests passing (`uv run pytest tests/unit/test_nlu_models.py -v`)
- [ ] Mypy passes (`uv run mypy src/soni/du/models.py`)
- [ ] Ruff passes (`uv run ruff check src/soni/du/models.py`)

### Validación Manual

**Comandos para validar:**

```bash
# Type checking
uv run mypy src/soni/du/models.py

# Tests
uv run pytest tests/unit/test_nlu_models.py -v

# Linting
uv run ruff check src/soni/du/models.py
uv run ruff format src/soni/du/models.py
```

**Resultado esperado:**
- Mypy shows no errors
- All tests pass
- Ruff shows no linting errors
- Models can be imported and instantiated correctly

### Referencias

- [docs/implementation/03-phase-3-nlu.md](../../docs/implementation/03-phase-3-nlu.md) - Task 3.1
- [docs/design/09-dspy-optimization.md](../../docs/design/09-dspy-optimization.md) - Structured types design
- [Pydantic documentation](https://docs.pydantic.dev/)

### Notas Adicionales

- All models use Pydantic v2 syntax
- Confidence fields must validate bounds (0.0-1.0)
- Use `default_factory` for mutable defaults (lists, dicts)
- MessageType enum values are lowercase strings
- These models will replace string-based inputs in signatures and modules
