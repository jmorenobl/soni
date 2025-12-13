## Task: 3.5 - Training Data Examples

**ID de tarea:** 305
**Hito:** Phase 3 - NLU System with DSPy
**Dependencias:** Task 301 (Pydantic Models)
**Duración estimada:** 1-2 horas

### Objetivo

Create example training data for DSPy optimization, demonstrating how to prepare structured training examples using Pydantic models and `dspy.Example`.

### Contexto

Training examples are required for DSPy optimization (MIPROv2, BootstrapFewShot, etc.). This task creates example data following the structured type format, showing how to prepare training data for the flight booking domain.

**Reference:** [docs/implementation/03-phase-3-nlu.md](../../docs/implementation/03-phase-3-nlu.md) - Task 3.5

### Entregables

- [ ] `create_flight_booking_examples()` function created
- [ ] Examples use structured types (`DialogueContext`, `dspy.History`, `NLUOutput`)
- [ ] Examples cover major scenarios (intent detection, slot extraction, corrections)
- [ ] Examples use `dspy.Example` with `.with_inputs()` method
- [ ] Documentation included
- [ ] File created in `examples/training/` directory

### Implementación Detallada

#### Paso 1: Create training examples file

**Archivo(s) a crear/modificar:** `examples/training/flight_booking_examples.py`

**Código específico:**

```python
"""Training examples for flight booking domain using structured types."""

import dspy

from soni.du.models import DialogueContext, MessageType, NLUOutput, SlotValue


def create_flight_booking_examples() -> list[dspy.Example]:
    """Create training examples for flight booking domain.

    Returns:
        List of dspy.Example objects with structured inputs and outputs
    """
    examples = []

    # Example 1: Intent detection
    examples.append(
        dspy.Example(
            user_message="I want to book a flight",
            history=dspy.History(messages=[]),
            context=DialogueContext(
                current_slots={},
                available_actions=["book_flight", "search_flights"],
                available_flows=["book_flight"],
                current_flow="none",
                expected_slots=["origin", "destination", "departure_date"],
            ),
            current_datetime="2024-12-02T10:00:00",
            result=NLUOutput(
                message_type=MessageType.INTERRUPTION,
                command="book_flight",
                slots=[],
                confidence=0.95,
                reasoning="User explicitly states intent to book a flight",
            ),
        ).with_inputs("user_message", "history", "context", "current_datetime")
    )

    # Example 2: Slot extraction
    examples.append(
        dspy.Example(
            user_message="From Madrid to Barcelona",
            history=dspy.History(
                messages=[
                    {
                        "role": "user",
                        "content": "I want to book a flight",
                    },
                    {
                        "role": "assistant",
                        "content": "Where are you departing from?",
                    },
                ]
            ),
            context=DialogueContext(
                current_slots={},
                available_actions=["book_flight"],
                available_flows=["book_flight"],
                current_flow="book_flight",
                expected_slots=["origin", "destination", "departure_date"],
            ),
            current_datetime="2024-12-02T10:00:00",
            result=NLUOutput(
                message_type=MessageType.SLOT_VALUE,
                command="book_flight",
                slots=[
                    SlotValue(name="origin", value="Madrid", confidence=0.9),
                    SlotValue(name="destination", value="Barcelona", confidence=0.9),
                ],
                confidence=0.9,
                reasoning="User provides origin and destination when expected",
            ),
        ).with_inputs("user_message", "history", "context", "current_datetime")
    )

    # Example 3: Correction
    examples.append(
        dspy.Example(
            user_message="Actually, make it Paris instead",
            history=dspy.History(
                messages=[
                    {
                        "role": "user",
                        "content": "I want to go to Barcelona",
                    },
                    {
                        "role": "assistant",
                        "content": "Got it, Barcelona. When would you like to travel?",
                    },
                ]
            ),
            context=DialogueContext(
                current_slots={"destination": "Barcelona"},
                available_actions=["book_flight"],
                available_flows=["book_flight"],
                current_flow="book_flight",
                expected_slots=["departure_date"],
            ),
            current_datetime="2024-12-02T10:00:00",
            result=NLUOutput(
                message_type=MessageType.CORRECTION,
                command="book_flight",
                slots=[
                    SlotValue(name="destination", value="Paris", confidence=0.95),
                ],
                confidence=0.95,
                reasoning="User corrects previous destination value",
            ),
        ).with_inputs("user_message", "history", "context", "current_datetime")
    )

    # Example 4: Modification request
    examples.append(
        dspy.Example(
            user_message="Can I change the departure date?",
            history=dspy.History(
                messages=[
                    {
                        "role": "user",
                        "content": "I want to book a flight from Madrid to Paris on 2024-12-15",
                    },
                    {
                        "role": "assistant",
                        "content": "Flight booked for December 15th. Anything else?",
                    },
                ]
            ),
            context=DialogueContext(
                current_slots={
                    "origin": "Madrid",
                    "destination": "Paris",
                    "departure_date": "2024-12-15",
                },
                available_actions=["book_flight", "modify_booking"],
                available_flows=["book_flight"],
                current_flow="book_flight",
                expected_slots=["departure_date"],
            ),
            current_datetime="2024-12-02T10:00:00",
            result=NLUOutput(
                message_type=MessageType.MODIFICATION,
                command="modify_booking",
                slots=[],
                confidence=0.9,
                reasoning="User requests to modify existing booking",
            ),
        ).with_inputs("user_message", "history", "context", "current_datetime")
    )

    return examples
```

**Explicación:**
- Create new file in `examples/training/` directory
- Use structured types throughout (`DialogueContext`, `dspy.History`, `NLUOutput`)
- Create examples covering major scenarios:
  - Intent detection (new flow start)
  - Slot extraction (providing values)
  - Correction (fixing previous value)
  - Modification (requesting to change)
- Use `dspy.Example` with `.with_inputs()` to specify input fields
- Include proper docstrings

### Tests Requeridos

**Archivo de tests:** `tests/unit/test_training_examples.py` (optional, but recommended)

**Tests específicos a implementar:**

```python
import pytest
import dspy
from examples.training.flight_booking_examples import create_flight_booking_examples
from soni.du.models import NLUOutput, MessageType

def test_create_flight_booking_examples():
    """Test that examples are created correctly."""
    # Arrange & Act
    examples = create_flight_booking_examples()

    # Assert
    assert len(examples) > 0
    assert all(isinstance(ex, dspy.Example) for ex in examples)

def test_examples_have_structured_types():
    """Test that examples use structured types."""
    # Arrange & Act
    examples = create_flight_booking_examples()
    first_example = examples[0]

    # Assert
    assert hasattr(first_example, "context")
    assert hasattr(first_example, "history")
    assert hasattr(first_example, "result")
    assert isinstance(first_example.result, NLUOutput)

def test_examples_cover_scenarios():
    """Test that examples cover major scenarios."""
    # Arrange & Act
    examples = create_flight_booking_examples()
    message_types = [ex.result.message_type for ex in examples]

    # Assert
    assert MessageType.INTERRUPTION in message_types
    assert MessageType.SLOT_VALUE in message_types
    assert MessageType.CORRECTION in message_types or MessageType.MODIFICATION in message_types
```

### Criterios de Éxito

- [ ] Example data created
- [ ] Covers major scenarios (intent detection, slot extraction, corrections, modifications)
- [ ] Uses structured types throughout
- [ ] Documentation included
- [ ] File created in correct location (`examples/training/`)
- [ ] Examples can be imported and used

### Validación Manual

**Comandos para validar:**

```bash
# Import and verify examples
uv run python -c "from examples.training.flight_booking_examples import create_flight_booking_examples; examples = create_flight_booking_examples(); print(f'Created {len(examples)} examples')"

# Type checking (if examples are in src/)
uv run mypy examples/training/flight_booking_examples.py

# Linting
uv run ruff check examples/training/flight_booking_examples.py
uv run ruff format examples/training/flight_booking_examples.py
```

**Resultado esperado:**
- Examples can be imported successfully
- Examples use structured types
- Examples cover multiple scenarios
- No linting errors

### Referencias

- [docs/implementation/03-phase-3-nlu.md](../../docs/implementation/03-phase-3-nlu.md) - Task 3.5
- [docs/design/09-dspy-optimization.md](../../docs/design/09-dspy-optimization.md) - DSPy optimization guide
- [DSPy documentation](https://dspy-docs.vercel.app/) - Example format

### Notas Adicionales

- Examples use structured types (`DialogueContext`, `dspy.History`, `NLUOutput`)
- Use `.with_inputs()` to specify which fields are inputs for optimization
- Include diverse scenarios to demonstrate different message types
- Examples should be realistic and representative of actual use cases
- This file serves as a template for creating domain-specific training data
- Directory `examples/training/` may need to be created if it doesn't exist
