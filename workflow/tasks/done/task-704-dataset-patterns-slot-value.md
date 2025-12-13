## Task: 704 - Dataset Pattern: SLOT_VALUE

**ID de tarea:** 704
**Hito:** Dataset Creation for NLU Optimization
**Dependencias:** Task 701 (Base), Task 702 (Flight Booking), Task 703 (Additional Domains)
**Duración estimada:** 3-4 horas

### Objetivo

Implement the SLOT_VALUE pattern generator, which creates training examples for when users provide direct answers to slot prompts or provide multiple slots in a single message.

### Contexto

SLOT_VALUE is the most fundamental pattern - it represents users answering questions or providing information. This pattern appears in two contexts:

1. **Cold Start**: User provides multiple slots in first message
   - Example: "I want to fly from Madrid to Barcelona tomorrow"

2. **Ongoing**: User answers specific slot prompt
   - Example: Bot: "Where to?" → User: "Barcelona"

This is the highest-frequency pattern and will have the most examples in the dataset.

**Reference:** docs/design/10-dsl-specification/06-patterns.md - SLOT_VALUE pattern

### Entregables

- [ ] `src/soni/dataset/patterns/slot_value.py` implemented
- [ ] `SlotValueGenerator` class following `PatternGenerator` interface
- [ ] Examples for both cold_start and ongoing contexts
- [ ] Examples across all 4 domains
- [ ] Unit tests in `tests/unit/test_dataset_patterns.py`
- [ ] Target: ~24 examples (4 domains × 2 contexts × 3 examples)

### Implementación Detallada

#### Paso 1: Create slot_value.py

**Archivo:** `src/soni/dataset/patterns/slot_value.py`

**Código específico:**

```python
"""SLOT_VALUE pattern generator.

This pattern represents users providing direct answers to slot prompts
or providing multiple slots in a single utterance.

Examples:
    Cold start: "Book a flight from Madrid to Barcelona tomorrow"
    Ongoing: Bot: "Where to?" → User: "Barcelona"
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


class SlotValueGenerator(PatternGenerator):
    """Generates SLOT_VALUE pattern examples."""

    @property
    def message_type(self) -> MessageType:
        return MessageType.SLOT_VALUE

    def generate_examples(
        self,
        domain_config: DomainConfig,
        context_type: Literal["cold_start", "ongoing"],
        count: int = 3,
    ) -> list[ExampleTemplate]:
        """Generate SLOT_VALUE examples.

        Args:
            domain_config: Domain configuration
            context_type: "cold_start" or "ongoing"
            count: Number of examples to generate

        Returns:
            List of example templates
        """
        if context_type == "cold_start":
            return self._generate_cold_start_examples(domain_config, count)
        else:
            return self._generate_ongoing_examples(domain_config, count)

    def _generate_cold_start_examples(
        self,
        domain_config: DomainConfig,
        count: int,
    ) -> list[ExampleTemplate]:
        """Generate cold start examples (multi-slot extraction).

        Users provide multiple slots in first message without being prompted.

        Args:
            domain_config: Domain configuration
            count: Number of examples to generate

        Returns:
            List of example templates
        """
        examples = []

        if domain_config.name == "flight_booking":
            from soni.dataset.domains.flight_booking import CITIES, DATES_RELATIVE

            # Example 1: Origin + Destination
            examples.append(
                ExampleTemplate(
                    user_message=f"I want to fly from {CITIES[0]} to {CITIES[1]}",
                    conversation_context=ConversationContext(
                        history=dspy.History(messages=[]),
                        current_slots={},
                        current_flow="none",
                        expected_slots=list(domain_config.slots.keys()),
                    ),
                    expected_output=NLUOutput(
                        message_type=MessageType.INTERRUPTION,  # Starting new flow
                        command="book_flight",
                        slots=[
                            SlotValue(name="origin", value=CITIES[0], confidence=0.9),
                            SlotValue(name="destination", value=CITIES[1], confidence=0.9),
                        ],
                        confidence=0.9,
                        reasoning=f"User initiates flight booking with origin and destination",
                    ),
                    domain=domain_config.name,
                    pattern="slot_value",
                    context_type="cold_start",
                    current_datetime="2024-12-11T10:00:00",
                )
            )

            # Example 2: Origin + Destination + Date
            examples.append(
                ExampleTemplate(
                    user_message=f"Book a flight from {CITIES[2]} to {CITIES[3]} {DATES_RELATIVE[0]}",
                    conversation_context=ConversationContext(
                        history=dspy.History(messages=[]),
                        current_slots={},
                        current_flow="none",
                        expected_slots=list(domain_config.slots.keys()),
                    ),
                    expected_output=NLUOutput(
                        message_type=MessageType.INTERRUPTION,
                        command="book_flight",
                        slots=[
                            SlotValue(name="origin", value=CITIES[2], confidence=0.95),
                            SlotValue(name="destination", value=CITIES[3], confidence=0.95),
                            SlotValue(name="departure_date", value=DATES_RELATIVE[0], confidence=0.9),
                        ],
                        confidence=0.93,
                        reasoning="User provides complete booking information upfront",
                    ),
                    domain=domain_config.name,
                    pattern="slot_value",
                    context_type="cold_start",
                    current_datetime="2024-12-11T10:00:00",
                )
            )

            # Example 3: Destination only (partial info)
            examples.append(
                ExampleTemplate(
                    user_message=f"I need a flight to {CITIES[4]}",
                    conversation_context=ConversationContext(
                        history=dspy.History(messages=[]),
                        current_slots={},
                        current_flow="none",
                        expected_slots=list(domain_config.slots.keys()),
                    ),
                    expected_output=NLUOutput(
                        message_type=MessageType.INTERRUPTION,
                        command="book_flight",
                        slots=[
                            SlotValue(name="destination", value=CITIES[4], confidence=0.9),
                        ],
                        confidence=0.9,
                        reasoning="User provides only destination, system will ask for other slots",
                    ),
                    domain=domain_config.name,
                    pattern="slot_value",
                    context_type="cold_start",
                    current_datetime="2024-12-11T10:00:00",
                )
            )

        elif domain_config.name == "hotel_booking":
            from soni.dataset.domains.hotel_booking import CITIES

            examples.append(
                ExampleTemplate(
                    user_message=f"Book a hotel in {CITIES[0]}",
                    conversation_context=ConversationContext(
                        history=dspy.History(messages=[]),
                        current_slots={},
                        current_flow="none",
                        expected_slots=list(domain_config.slots.keys()),
                    ),
                    expected_output=NLUOutput(
                        message_type=MessageType.INTERRUPTION,
                        command="book_hotel",
                        slots=[
                            SlotValue(name="location", value=CITIES[0], confidence=0.9),
                        ],
                        confidence=0.9,
                        reasoning="User initiates hotel booking with location",
                    ),
                    domain=domain_config.name,
                    pattern="slot_value",
                    context_type="cold_start",
                    current_datetime="2024-12-11T10:00:00",
                )
            )

        elif domain_config.name == "restaurant":
            from soni.dataset.domains.restaurant import CITIES, PARTY_SIZES

            examples.append(
                ExampleTemplate(
                    user_message=f"I need a table for {PARTY_SIZES[0]} in {CITIES[0]}",
                    conversation_context=ConversationContext(
                        history=dspy.History(messages=[]),
                        current_slots={},
                        current_flow="none",
                        expected_slots=list(domain_config.slots.keys()),
                    ),
                    expected_output=NLUOutput(
                        message_type=MessageType.INTERRUPTION,
                        command="book_table",
                        slots=[
                            SlotValue(name="party_size", value=str(PARTY_SIZES[0]), confidence=0.95),
                            SlotValue(name="location", value=CITIES[0], confidence=0.9),
                        ],
                        confidence=0.92,
                        reasoning="User provides party size and location for restaurant",
                    ),
                    domain=domain_config.name,
                    pattern="slot_value",
                    context_type="cold_start",
                    current_datetime="2024-12-11T10:00:00",
                )
            )

        elif domain_config.name == "ecommerce":
            from soni.dataset.domains.ecommerce import PRODUCTS

            examples.append(
                ExampleTemplate(
                    user_message=f"I want to buy a {PRODUCTS[0]}",
                    conversation_context=ConversationContext(
                        history=dspy.History(messages=[]),
                        current_slots={},
                        current_flow="none",
                        expected_slots=list(domain_config.slots.keys()),
                    ),
                    expected_output=NLUOutput(
                        message_type=MessageType.INTERRUPTION,
                        command="search_product",
                        slots=[
                            SlotValue(name="product", value=PRODUCTS[0], confidence=0.95),
                        ],
                        confidence=0.95,
                        reasoning="User specifies product to search for",
                    ),
                    domain=domain_config.name,
                    pattern="slot_value",
                    context_type="cold_start",
                    current_datetime="2024-12-11T10:00:00",
                )
            )

        return examples[:count]

    def _generate_ongoing_examples(
        self,
        domain_config: DomainConfig,
        count: int,
    ) -> list[ExampleTemplate]:
        """Generate ongoing examples (answering specific prompts).

        User provides answer to a specific slot being asked.

        Args:
            domain_config: Domain configuration
            count: Number of examples to generate

        Returns:
            List of example templates
        """
        examples = []

        if domain_config.name == "flight_booking":
            from soni.dataset.domains.flight_booking import (
                CITIES,
                DATES_RELATIVE,
                create_context_after_origin,
                create_context_after_origin_destination,
            )

            # Example 1: Answering destination prompt
            examples.append(
                ExampleTemplate(
                    user_message=CITIES[5],
                    conversation_context=create_context_after_origin(origin=CITIES[0]),
                    expected_output=NLUOutput(
                        message_type=MessageType.SLOT_VALUE,
                        command="book_flight",
                        slots=[
                            SlotValue(name="destination", value=CITIES[5], confidence=0.95),
                        ],
                        confidence=0.95,
                        reasoning="User directly answers destination prompt",
                    ),
                    domain=domain_config.name,
                    pattern="slot_value",
                    context_type="ongoing",
                    current_datetime="2024-12-11T10:00:00",
                )
            )

            # Example 2: Answering date prompt
            examples.append(
                ExampleTemplate(
                    user_message=DATES_RELATIVE[1],
                    conversation_context=create_context_after_origin_destination(
                        origin=CITIES[0],
                        destination=CITIES[1],
                    ),
                    expected_output=NLUOutput(
                        message_type=MessageType.SLOT_VALUE,
                        command="book_flight",
                        slots=[
                            SlotValue(name="departure_date", value=DATES_RELATIVE[1], confidence=0.9),
                        ],
                        confidence=0.9,
                        reasoning="User provides departure date when prompted",
                    ),
                    domain=domain_config.name,
                    pattern="slot_value",
                    context_type="ongoing",
                    current_datetime="2024-12-11T10:00:00",
                )
            )

            # Example 3: Multiple slots in answer
            examples.append(
                ExampleTemplate(
                    user_message=f"{CITIES[6]} to {CITIES[7]}",
                    conversation_context=ConversationContext(
                        history=dspy.History(messages=[
                            {
                                "user_message": "Book a flight",
                                "result": {"command": "book_flight", "message_type": "interruption"},
                            },
                        ]),
                        current_slots={},
                        current_flow="book_flight",
                        expected_slots=["origin", "destination", "departure_date"],
                    ),
                    expected_output=NLUOutput(
                        message_type=MessageType.SLOT_VALUE,
                        command="book_flight",
                        slots=[
                            SlotValue(name="origin", value=CITIES[6], confidence=0.9),
                            SlotValue(name="destination", value=CITIES[7], confidence=0.9),
                        ],
                        confidence=0.9,
                        reasoning="User provides both origin and destination in response",
                    ),
                    domain=domain_config.name,
                    pattern="slot_value",
                    context_type="ongoing",
                    current_datetime="2024-12-11T10:00:00",
                )
            )

        elif domain_config.name == "hotel_booking":
            from soni.dataset.domains.hotel_booking import (
                CITIES,
                create_context_after_location,
            )

            examples.append(
                ExampleTemplate(
                    user_message="tomorrow",
                    conversation_context=create_context_after_location(location=CITIES[0]),
                    expected_output=NLUOutput(
                        message_type=MessageType.SLOT_VALUE,
                        command="book_hotel",
                        slots=[
                            SlotValue(name="checkin_date", value="tomorrow", confidence=0.9),
                        ],
                        confidence=0.9,
                        reasoning="User provides check-in date",
                    ),
                    domain=domain_config.name,
                    pattern="slot_value",
                    context_type="ongoing",
                    current_datetime="2024-12-11T10:00:00",
                )
            )

        elif domain_config.name == "restaurant":
            from soni.dataset.domains.restaurant import (
                TIMES,
                create_context_after_location,
            )

            examples.append(
                ExampleTemplate(
                    user_message=TIMES[0],
                    conversation_context=create_context_after_location(location="Madrid"),
                    expected_output=NLUOutput(
                        message_type=MessageType.SLOT_VALUE,
                        command="book_table",
                        slots=[
                            SlotValue(name="time", value=TIMES[0], confidence=0.95),
                        ],
                        confidence=0.95,
                        reasoning="User specifies desired time",
                    ),
                    domain=domain_config.name,
                    pattern="slot_value",
                    context_type="ongoing",
                    current_datetime="2024-12-11T10:00:00",
                )
            )

        elif domain_config.name == "ecommerce":
            from soni.dataset.domains.ecommerce import (
                COLORS,
                create_context_after_product,
            )

            examples.append(
                ExampleTemplate(
                    user_message=COLORS[0],
                    conversation_context=create_context_after_product(product="laptop"),
                    expected_output=NLUOutput(
                        message_type=MessageType.SLOT_VALUE,
                        command="search_product",
                        slots=[
                            SlotValue(name="color", value=COLORS[0], confidence=0.9),
                        ],
                        confidence=0.9,
                        reasoning="User specifies color preference",
                    ),
                    domain=domain_config.name,
                    pattern="slot_value",
                    context_type="ongoing",
                    current_datetime="2024-12-11T10:00:00",
                )
            )

        return examples[:count]
```

**Explicación:**
- Implements `PatternGenerator` interface
- Handles both cold_start and ongoing contexts
- Domain-specific logic using imported data
- Uses domain helper functions for context creation
- Returns limited number of examples per request

#### Paso 2: Update patterns package

**Archivo:** `src/soni/dataset/patterns/__init__.py`

**Código específico:**

```python
"""Pattern generators for conversational patterns.

Each pattern generator creates training examples for a specific MessageType.
"""

from soni.dataset.patterns.slot_value import SlotValueGenerator

# Registry of all pattern generators
ALL_PATTERN_GENERATORS = {
    "slot_value": SlotValueGenerator(),
}

__all__ = [
    "SlotValueGenerator",
    "ALL_PATTERN_GENERATORS",
]
```

### TDD Cycle (MANDATORY for new features)

#### Red Phase: Write Failing Tests

**Test file:** `tests/unit/test_dataset_patterns.py`

**Código:**

```python
"""Unit tests for pattern generators."""

import pytest
import dspy
from soni.dataset.patterns.slot_value import SlotValueGenerator
from soni.dataset.domains.flight_booking import FLIGHT_BOOKING
from soni.dataset.domains.hotel_booking import HOTEL_BOOKING
from soni.du.models import MessageType


def test_slot_value_generator_message_type():
    """Test SlotValueGenerator returns correct message_type."""
    # Arrange
    generator = SlotValueGenerator()

    # Assert
    assert generator.message_type == MessageType.SLOT_VALUE


def test_slot_value_generator_cold_start_flight_booking():
    """Test generating cold start examples for flight booking."""
    # Arrange
    generator = SlotValueGenerator()

    # Act
    examples = generator.generate_examples(
        domain_config=FLIGHT_BOOKING,
        context_type="cold_start",
        count=3,
    )

    # Assert
    assert len(examples) == 3
    assert all(ex.context_type == "cold_start" for ex in examples)
    assert all(ex.domain == "flight_booking" for ex in examples)
    assert all(ex.pattern == "slot_value" for ex in examples)
    # Cold start should use INTERRUPTION (starting new flow)
    assert all(ex.expected_output.message_type == MessageType.INTERRUPTION for ex in examples)


def test_slot_value_generator_ongoing_flight_booking():
    """Test generating ongoing examples for flight booking."""
    # Arrange
    generator = SlotValueGenerator()

    # Act
    examples = generator.generate_examples(
        domain_config=FLIGHT_BOOKING,
        context_type="ongoing",
        count=3,
    )

    # Assert
    assert len(examples) == 3
    assert all(ex.context_type == "ongoing" for ex in examples)
    assert all(ex.domain == "flight_booking" for ex in examples)
    # Ongoing should use SLOT_VALUE
    assert all(ex.expected_output.message_type == MessageType.SLOT_VALUE for ex in examples)
    # Ongoing examples should have history
    assert all(len(ex.conversation_context.history.messages) > 0 for ex in examples)


def test_slot_value_generator_respects_count():
    """Test generator respects count parameter."""
    # Arrange
    generator = SlotValueGenerator()

    # Act
    examples_2 = generator.generate_examples(FLIGHT_BOOKING, "cold_start", count=2)
    examples_5 = generator.generate_examples(FLIGHT_BOOKING, "cold_start", count=5)

    # Assert
    assert len(examples_2) <= 2  # May have fewer if not enough variations
    assert len(examples_5) <= 5


def test_slot_value_generator_works_with_all_domains():
    """Test generator works with all domains."""
    # Arrange
    generator = SlotValueGenerator()
    from soni.dataset.domains import ALL_DOMAINS

    # Act & Assert - should not raise
    for domain_name, domain_config in ALL_DOMAINS.items():
        examples_cold = generator.generate_examples(domain_config, "cold_start", count=1)
        examples_ongoing = generator.generate_examples(domain_config, "ongoing", count=1)

        assert len(examples_cold) >= 1, f"No cold_start examples for {domain_name}"
        assert len(examples_ongoing) >= 1, f"No ongoing examples for {domain_name}"


def test_slot_value_examples_have_required_fields():
    """Test generated examples have all required fields."""
    # Arrange
    generator = SlotValueGenerator()

    # Act
    examples = generator.generate_examples(FLIGHT_BOOKING, "cold_start", count=1)
    example = examples[0]

    # Assert
    assert example.user_message
    assert example.conversation_context is not None
    assert example.expected_output is not None
    assert example.domain == "flight_booking"
    assert example.pattern == "slot_value"
    assert example.expected_output.command
    assert isinstance(example.expected_output.slots, list)
    assert 0.0 <= example.expected_output.confidence <= 1.0


def test_slot_value_examples_convert_to_dspy_example():
    """Test examples can be converted to dspy.Example."""
    # Arrange
    generator = SlotValueGenerator()
    templates = generator.generate_examples(FLIGHT_BOOKING, "cold_start", count=1)
    template = templates[0]

    # Act
    example = template.to_dspy_example(FLIGHT_BOOKING)

    # Assert
    assert isinstance(example, dspy.Example)
    assert hasattr(example, "user_message")
    assert hasattr(example, "history")
    assert hasattr(example, "context")
    assert hasattr(example, "result")
```

**Verify tests fail:**
```bash
uv run pytest tests/unit/test_dataset_patterns.py -v
# Expected: FAILED (module not implemented yet)
```

**Commit:**
```bash
git add tests/
git commit -m "test: add failing tests for SLOT_VALUE pattern"
```

#### Green Phase: Make Tests Pass

Implement the code as specified in "Implementación Detallada" section.

**Verify tests pass:**
```bash
uv run pytest tests/unit/test_dataset_patterns.py -v
# Expected: PASSED ✅
```

**Commit:**
```bash
git add src/ tests/
git commit -m "feat: implement SLOT_VALUE pattern generator"
```

#### Refactor Phase: Improve Design

- Add more example variations
- Ensure consistent confidence scores
- Add more detailed reasoning
- Tests must still pass!

**Commit:**
```bash
git add src/
git commit -m "refactor: improve SLOT_VALUE pattern with more variations"
```

### Criterios de Éxito

- [ ] `SlotValueGenerator` implemented following interface
- [ ] Works with all 4 domains
- [ ] Handles both cold_start and ongoing contexts
- [ ] Examples have proper confidence scores and reasoning
- [ ] All tests pass
- [ ] Mypy passes with no errors
- [ ] Ruff passes with no errors
- [ ] Generated examples convert to dspy.Example correctly

### Validación Manual

**Comandos para validar:**

```bash
# Type checking
uv run mypy src/soni/dataset/patterns/

# Tests
uv run pytest tests/unit/test_dataset_patterns.py -v

# Linting
uv run ruff check src/soni/dataset/patterns/
uv run ruff format src/soni/dataset/patterns/

# Manual test - generate examples
uv run python -c "
from soni.dataset.patterns.slot_value import SlotValueGenerator
from soni.dataset.domains import FLIGHT_BOOKING

gen = SlotValueGenerator()
examples = gen.generate_examples(FLIGHT_BOOKING, 'cold_start', count=2)
print(f'Generated {len(examples)} examples')
for ex in examples:
    print(f'  - {ex.user_message[:50]}...')
"
```

**Resultado esperado:**
- All tests pass
- No mypy or ruff errors
- Examples are generated successfully

### Referencias

- docs/design/10-dsl-specification/06-patterns.md - Pattern definitions
- docs/design/06-nlu-system.md - NLU architecture

### Notas Adicionales

- SLOT_VALUE is the most common pattern, should have most examples
- Cold start examples use INTERRUPTION message_type (starting new flow)
- Ongoing examples use SLOT_VALUE message_type (answering prompt)
- Confidence scores should be realistic (0.85-0.95 typical)
- Reasoning should explain what the user is doing
