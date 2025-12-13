## Task: 705 - Dataset Patterns: CORRECTION and MODIFICATION

**ID de tarea:** 705
**Hito:** Dataset Creation for NLU Optimization
**Dependencias:** Task 704 (SLOT_VALUE pattern)
**Duración estimada:** 3-4 horas

### Objetivo

Implement CORRECTION and MODIFICATION pattern generators for when users fix or change previously provided slot values.

### Contexto

These two patterns handle user corrections:

**CORRECTION (Reactive)**: User realizes they made a mistake
- "No, I said Barcelona not Madrid"
- "Actually, I meant tomorrow"
- Triggered by confirmation or realization of error

**MODIFICATION (Proactive)**: User explicitly asks to change a value
- "Change the destination to London"
- "Can I modify the departure date?"
- Explicit request to update

Both patterns only occur in **ongoing** context (requires history).

**Reference:** docs/design/10-dsl-specification/06-patterns.md

### Entregables

- [ ] `src/soni/dataset/patterns/correction.py` implemented
- [ ] `src/soni/dataset/patterns/modification.py` implemented
- [ ] `CorrectionGenerator` class
- [ ] `ModificationGenerator` class
- [ ] Examples across all 4 domains (ongoing context only)
- [ ] Unit tests extended in `tests/unit/test_dataset_patterns.py`
- [ ] Target: ~16 examples (2 patterns × 4 domains × 2 examples)

### Implementación Detallada

#### Paso 1: Create correction.py

**Archivo:** `src/soni/dataset/patterns/correction.py`

**Código específico:**

```python
"""CORRECTION pattern generator.

Reactive corrections - user realizes they made a mistake.

Examples:
    - Bot: "Flying to Madrid, correct?"
    - User: "No, I meant Barcelona"
"""

import dspy
from typing import Literal
from soni.dataset.base import (
    PatternGenerator,
    ExampleTemplate,
    ConversationContext,
    DomainConfig,
)
from soni.du.models import MessageType, NLUOutput, SlotValue


class CorrectionGenerator(PatternGenerator):
    """Generates CORRECTION pattern examples."""

    @property
    def message_type(self) -> MessageType:
        return MessageType.CORRECTION

    def generate_examples(
        self,
        domain_config: DomainConfig,
        context_type: Literal["cold_start", "ongoing"],
        count: int = 3,
    ) -> list[ExampleTemplate]:
        """Generate CORRECTION examples (ongoing only)."""
        if context_type == "cold_start":
            return []  # Corrections only happen in ongoing conversations

        return self._generate_ongoing_examples(domain_config, count)

    def _generate_ongoing_examples(
        self,
        domain_config: DomainConfig,
        count: int,
    ) -> list[ExampleTemplate]:
        """Generate correction examples."""
        examples = []

        if domain_config.name == "flight_booking":
            from soni.dataset.domains.flight_booking import (
                CITIES,
                create_context_before_confirmation,
            )

            # Example 1: Correcting destination
            examples.append(
                ExampleTemplate(
                    user_message=f"No, I said {CITIES[5]} not {CITIES[1]}",
                    conversation_context=create_context_before_confirmation(
                        origin=CITIES[0],
                        destination=CITIES[1],  # Wrong value
                        departure_date="tomorrow",
                    ),
                    expected_output=NLUOutput(
                        message_type=MessageType.CORRECTION,
                        command="book_flight",
                        slots=[
                            SlotValue(name="destination", value=CITIES[5], confidence=0.9),
                        ],
                        confidence=0.9,
                        reasoning="User corrects destination value after confirmation prompt",
                    ),
                    domain=domain_config.name,
                    pattern="correction",
                    context_type="ongoing",
                    current_datetime="2024-12-11T10:00:00",
                )
            )

            # Example 2: Correcting date with "actually"
            examples.append(
                ExampleTemplate(
                    user_message="Actually, I want to leave next Monday",
                    conversation_context=create_context_before_confirmation(
                        origin=CITIES[0],
                        destination=CITIES[1],
                        departure_date="tomorrow",  # Wrong value
                    ),
                    expected_output=NLUOutput(
                        message_type=MessageType.CORRECTION,
                        command="book_flight",
                        slots=[
                            SlotValue(name="departure_date", value="next Monday", confidence=0.9),
                        ],
                        confidence=0.9,
                        reasoning="User corrects departure date using 'actually' signal",
                    ),
                    domain=domain_config.name,
                    pattern="correction",
                    context_type="ongoing",
                    current_datetime="2024-12-11T10:00:00",
                )
            )

        elif domain_config.name == "hotel_booking":
            from soni.dataset.domains.hotel_booking import CITIES

            examples.append(
                ExampleTemplate(
                    user_message=f"No wait, {CITIES[2]}, not {CITIES[0]}",
                    conversation_context=ConversationContext(
                        history=dspy.History(messages=[
                            {"user_message": f"Book hotel in {CITIES[0]}"},
                        ]),
                        current_slots={"location": CITIES[0]},
                        current_flow="book_hotel",
                        expected_slots=["checkin_date"],
                    ),
                    expected_output=NLUOutput(
                        message_type=MessageType.CORRECTION,
                        command="book_hotel",
                        slots=[
                            SlotValue(name="location", value=CITIES[2], confidence=0.9),
                        ],
                        confidence=0.9,
                        reasoning="User immediately corrects location",
                    ),
                    domain=domain_config.name,
                    pattern="correction",
                    context_type="ongoing",
                    current_datetime="2024-12-11T10:00:00",
                )
            )

        # Similar for restaurant and ecommerce...

        return examples[:count]
```

#### Paso 2: Create modification.py

**Archivo:** `src/soni/dataset/patterns/modification.py`

**Código específico:**

```python
"""MODIFICATION pattern generator.

Proactive modifications - user explicitly requests to change a value.

Examples:
    - "Change the destination to London"
    - "Can I modify the date?"
"""

import dspy
from typing import Literal
from soni.dataset.base import (
    PatternGenerator,
    ExampleTemplate,
    ConversationContext,
    DomainConfig,
)
from soni.du.models import MessageType, NLUOutput, SlotValue


class ModificationGenerator(PatternGenerator):
    """Generates MODIFICATION pattern examples."""

    @property
    def message_type(self) -> MessageType:
        return MessageType.MODIFICATION

    def generate_examples(
        self,
        domain_config: DomainConfig,
        context_type: Literal["cold_start", "ongoing"],
        count: int = 3,
    ) -> list[ExampleTemplate]:
        """Generate MODIFICATION examples (ongoing only)."""
        if context_type == "cold_start":
            return []  # Modifications only happen in ongoing conversations

        return self._generate_ongoing_examples(domain_config, count)

    def _generate_ongoing_examples(
        self,
        domain_config: DomainConfig,
        count: int,
    ) -> list[ExampleTemplate]:
        """Generate modification examples."""
        examples = []

        if domain_config.name == "flight_booking":
            from soni.dataset.domains.flight_booking import (
                CITIES,
                DATES_RELATIVE,
                create_context_before_confirmation,
            )

            # Example 1: Explicit change request
            examples.append(
                ExampleTemplate(
                    user_message=f"Change the destination to {CITIES[6]}",
                    conversation_context=create_context_before_confirmation(
                        origin=CITIES[0],
                        destination=CITIES[1],
                        departure_date="tomorrow",
                    ),
                    expected_output=NLUOutput(
                        message_type=MessageType.MODIFICATION,
                        command="book_flight",
                        slots=[
                            SlotValue(name="destination", value=CITIES[6], confidence=0.95),
                        ],
                        confidence=0.95,
                        reasoning="User explicitly requests to change destination",
                    ),
                    domain=domain_config.name,
                    pattern="modification",
                    context_type="ongoing",
                    current_datetime="2024-12-11T10:00:00",
                )
            )

            # Example 2: "Can I modify..."
            examples.append(
                ExampleTemplate(
                    user_message=f"Can I modify the date to {DATES_RELATIVE[2]}?",
                    conversation_context=create_context_before_confirmation(
                        origin=CITIES[0],
                        destination=CITIES[1],
                        departure_date=DATES_RELATIVE[0],
                    ),
                    expected_output=NLUOutput(
                        message_type=MessageType.MODIFICATION,
                        command="book_flight",
                        slots=[
                            SlotValue(name="departure_date", value=DATES_RELATIVE[2], confidence=0.9),
                        ],
                        confidence=0.9,
                        reasoning="User asks to modify departure date",
                    ),
                    domain=domain_config.name,
                    pattern="modification",
                    context_type="ongoing",
                    current_datetime="2024-12-11T10:00:00",
                )
            )

        # Similar for other domains...

        return examples[:count]
```

### TDD Cycle

**Tests to add to `tests/unit/test_dataset_patterns.py`:**

```python
from soni.dataset.patterns.correction import CorrectionGenerator
from soni.dataset.patterns.modification import ModificationGenerator


def test_correction_generator_message_type():
    """Test CorrectionGenerator returns correct message_type."""
    assert CorrectionGenerator().message_type == MessageType.CORRECTION


def test_correction_returns_empty_for_cold_start():
    """Test corrections only work in ongoing context."""
    generator = CorrectionGenerator()
    examples = generator.generate_examples(FLIGHT_BOOKING, "cold_start", count=3)
    assert len(examples) == 0


def test_correction_generates_ongoing_examples():
    """Test correction generates ongoing examples."""
    generator = CorrectionGenerator()
    examples = generator.generate_examples(FLIGHT_BOOKING, "ongoing", count=2)
    assert len(examples) >= 1
    assert all(ex.expected_output.message_type == MessageType.CORRECTION for ex in examples)


def test_modification_generator_message_type():
    """Test ModificationGenerator returns correct message_type."""
    assert ModificationGenerator().message_type == MessageType.MODIFICATION


def test_modification_generates_ongoing_examples():
    """Test modification generates ongoing examples."""
    generator = ModificationGenerator()
    examples = generator.generate_examples(FLIGHT_BOOKING, "ongoing", count=2)
    assert len(examples) >= 1
    assert all(ex.expected_output.message_type == MessageType.MODIFICATION for ex in examples)
```

### Criterios de Éxito

- [ ] Both generators implemented following interface
- [ ] Return empty list for cold_start (these patterns require history)
- [ ] Generate valid examples for ongoing context
- [ ] Examples across all domains
- [ ] All tests pass
- [ ] Mypy and Ruff pass

### Validación Manual

```bash
uv run pytest tests/unit/test_dataset_patterns.py -v -k "correction or modification"
uv run mypy src/soni/dataset/patterns/
uv run ruff check src/soni/dataset/patterns/
```

### Referencias

- docs/design/10-dsl-specification/06-patterns.md - Pattern definitions
- Task 704 - SLOT_VALUE pattern (template)

### Notas Adicionales

- Both patterns require conversation history (ongoing only)
- CORRECTION: reactive, user realizes mistake
- MODIFICATION: proactive, explicit change request
- Common signals: "no", "actually", "change", "modify", "wait"
