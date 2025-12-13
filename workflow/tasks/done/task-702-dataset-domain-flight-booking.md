## Task: 702 - Dataset Domain: Flight Booking

**ID de tarea:** 702
**Hito:** Dataset Creation for NLU Optimization
**Dependencias:** Task 701 (Dataset Base Infrastructure)
**Duración estimada:** 2-3 horas

### Objetivo

Implement the flight booking domain configuration and example data, which will be used by pattern generators to create training examples for the NLU system.

### Contexto

The flight booking domain is the primary domain for our dataset. It includes common slots like origin, destination, departure_date, return_date, passengers, and cabin class. This domain will serve as the template for other domains.

Flight booking is complex enough to demonstrate all conversational patterns while remaining familiar to most users.

**Reference:** docs/design/10-dsl-specification/ - Flow and slot definitions

### Entregables

- [ ] `src/soni/dataset/domains/flight_booking.py` implemented
- [ ] `FLIGHT_BOOKING` domain configuration defined
- [ ] Example data for cities, dates, cabin classes
- [ ] Helper functions for creating common conversation contexts
- [ ] Unit tests in `tests/unit/test_dataset_domains.py`
- [ ] Domain registered in builder (automatic discovery)

### Implementación Detallada

#### Paso 1: Create flight_booking.py

**Archivo:** `src/soni/dataset/domains/flight_booking.py`

**Código específico:**

```python
"""Flight booking domain configuration and example data.

This module defines the flight booking domain used for generating
training examples across all conversational patterns.
"""

from soni.dataset.base import DomainConfig

# Domain configuration
FLIGHT_BOOKING = DomainConfig(
    name="flight_booking",
    description="Book flights between cities with departure and return dates",
    available_flows=[
        "book_flight",
        "search_flights",
        "check_booking",
        "modify_booking",
        "cancel_booking",
    ],
    available_actions=[
        "search_flights",
        "book_flight",
        "modify_booking",
        "cancel_booking",
        "send_confirmation",
    ],
    slots={
        "origin": "city",
        "destination": "city",
        "departure_date": "date",
        "return_date": "date",
        "passengers": "number",
        "cabin_class": "string",
    },
    slot_prompts={
        "origin": "Which city are you departing from?",
        "destination": "Where would you like to fly to?",
        "departure_date": "When would you like to depart?",
        "return_date": "When would you like to return?",
        "passengers": "How many passengers will be traveling?",
        "cabin_class": "Which cabin class would you prefer? (economy, business, or first class)",
    },
)

# Example data for generating varied examples
CITIES = [
    "Madrid",
    "Barcelona",
    "Paris",
    "London",
    "New York",
    "Los Angeles",
    "Tokyo",
    "Rome",
    "Berlin",
    "Amsterdam",
]

DATES_RELATIVE = [
    "tomorrow",
    "next Monday",
    "next week",
    "in two weeks",
    "next month",
]

DATES_SPECIFIC = [
    "December 15th",
    "January 10th",
    "March 25th",
    "June 1st",
]

CABIN_CLASSES = [
    "economy",
    "business",
    "first class",
]

# Common passenger counts
PASSENGER_COUNTS = [1, 2, 3, 4]

# Utterance variations for different intents
BOOKING_UTTERANCES = [
    "I want to book a flight",
    "Book a flight",
    "I need to book a ticket",
    "Can you help me book a flight",
    "I'd like to make a flight reservation",
]

SEARCH_UTTERANCES = [
    "Search for flights",
    "Find flights",
    "Show me flights",
    "Can you search for available flights",
    "I want to see flight options",
]

CANCELLATION_UTTERANCES = [
    "Cancel",
    "Never mind",
    "Forget it",
    "I changed my mind",
    "Stop",
    "Cancel everything",
]

CONFIRMATION_POSITIVE = [
    "Yes",
    "Correct",
    "That's right",
    "Yes, that looks good",
    "Confirmed",
    "Yeah",
]

CONFIRMATION_NEGATIVE = [
    "No",
    "That's wrong",
    "No, that's not right",
    "Incorrect",
    "Nope",
]
```

**Explicación:**
- `FLIGHT_BOOKING`: Immutable domain configuration
- Example data arrays for generating varied examples
- Utterance variations to increase diversity
- All constants in UPPER_SNAKE_CASE following Python conventions

#### Paso 2: Create helper functions

**Agregar al mismo archivo `flight_booking.py`:**

```python
"""Helper functions for creating flight booking contexts."""

import dspy
from typing import Any
from soni.dataset.base import ConversationContext


def create_empty_flight_context() -> ConversationContext:
    """Create context for new flight booking conversation (no history).

    Returns:
        ConversationContext with empty history and no filled slots
    """
    return ConversationContext(
        history=dspy.History(messages=[]),
        current_slots={},
        current_flow="none",
        expected_slots=["origin", "destination", "departure_date"],
    )


def create_context_after_origin(origin: str = "Madrid") -> ConversationContext:
    """Create context after user provided origin.

    Args:
        origin: Origin city (default: "Madrid")

    Returns:
        ConversationContext with origin filled, asking for destination
    """
    return ConversationContext(
        history=dspy.History(messages=[
            {
                "user_message": "I want to book a flight",
                "result": {
                    "command": "book_flight",
                    "message_type": "interruption",
                },
            },
            {
                "user_message": f"From {origin}",
                "result": {
                    "command": "book_flight",
                    "message_type": "slot_value",
                    "slots": [{"name": "origin", "value": origin}],
                },
            },
        ]),
        current_slots={"origin": origin},
        current_flow="book_flight",
        expected_slots=["destination", "departure_date"],
    )


def create_context_after_origin_destination(
    origin: str = "Madrid",
    destination: str = "Barcelona",
) -> ConversationContext:
    """Create context after user provided origin and destination.

    Args:
        origin: Origin city (default: "Madrid")
        destination: Destination city (default: "Barcelona")

    Returns:
        ConversationContext with origin and destination filled
    """
    return ConversationContext(
        history=dspy.History(messages=[
            {
                "user_message": "I want to book a flight",
                "result": {"command": "book_flight", "message_type": "interruption"},
            },
            {
                "user_message": f"From {origin} to {destination}",
                "result": {
                    "command": "book_flight",
                    "message_type": "slot_value",
                    "slots": [
                        {"name": "origin", "value": origin},
                        {"name": "destination", "value": destination},
                    ],
                },
            },
        ]),
        current_slots={"origin": origin, "destination": destination},
        current_flow="book_flight",
        expected_slots=["departure_date"],
    )


def create_context_before_confirmation(
    origin: str = "Madrid",
    destination: str = "Barcelona",
    departure_date: str = "tomorrow",
) -> ConversationContext:
    """Create context right before confirmation step.

    All required slots filled, ready for confirmation.

    Args:
        origin: Origin city
        destination: Destination city
        departure_date: Departure date

    Returns:
        ConversationContext with all main slots filled
    """
    return ConversationContext(
        history=dspy.History(messages=[
            {
                "user_message": f"Book a flight from {origin} to {destination} {departure_date}",
                "result": {
                    "command": "book_flight",
                    "message_type": "interruption",
                    "slots": [
                        {"name": "origin", "value": origin},
                        {"name": "destination", "value": destination},
                        {"name": "departure_date", "value": departure_date},
                    ],
                },
            },
        ]),
        current_slots={
            "origin": origin,
            "destination": destination,
            "departure_date": departure_date,
        },
        current_flow="book_flight",
        expected_slots=[],  # All required slots filled
    )
```

**Explicación:**
- Helper functions create common conversation states
- Reduces boilerplate in pattern generators
- Each helper returns a ConversationContext ready to use
- Default values make tests more readable

#### Paso 3: Update domains package

**Archivo:** `src/soni/dataset/domains/__init__.py`

**Código específico:**

```python
"""Domain configurations for dataset generation.

Each domain represents a business context (e.g., flight booking, hotel booking)
with its own set of flows, actions, and slots.
"""

from soni.dataset.domains.flight_booking import FLIGHT_BOOKING

# Registry of all available domains
ALL_DOMAINS = {
    "flight_booking": FLIGHT_BOOKING,
}

__all__ = [
    "FLIGHT_BOOKING",
    "ALL_DOMAINS",
]
```

### TDD Cycle (MANDATORY for new features)

#### Red Phase: Write Failing Tests

**Test file:** `tests/unit/test_dataset_domains.py`

**Failing tests to write FIRST:**

```python
"""Unit tests for domain configurations."""

import pytest
import dspy
from soni.dataset.domains.flight_booking import (
    FLIGHT_BOOKING,
    CITIES,
    CABIN_CLASSES,
    create_empty_flight_context,
    create_context_after_origin,
    create_context_after_origin_destination,
    create_context_before_confirmation,
)
from soni.dataset.base import DomainConfig, ConversationContext


def test_flight_booking_domain_is_valid():
    """Test FLIGHT_BOOKING domain configuration is valid."""
    # Assert
    assert isinstance(FLIGHT_BOOKING, DomainConfig)
    assert FLIGHT_BOOKING.name == "flight_booking"
    assert len(FLIGHT_BOOKING.available_flows) > 0
    assert len(FLIGHT_BOOKING.available_actions) > 0
    assert len(FLIGHT_BOOKING.slots) > 0


def test_flight_booking_has_required_slots():
    """Test flight booking domain has all required slots."""
    # Arrange
    required_slots = ["origin", "destination", "departure_date"]

    # Assert
    for slot in required_slots:
        assert slot in FLIGHT_BOOKING.slots
        assert slot in FLIGHT_BOOKING.slot_prompts


def test_flight_booking_has_required_flows():
    """Test flight booking domain has common flows."""
    # Arrange
    required_flows = ["book_flight", "search_flights"]

    # Assert
    for flow in required_flows:
        assert flow in FLIGHT_BOOKING.available_flows


def test_cities_list_has_variety():
    """Test CITIES list has sufficient variety."""
    # Assert
    assert len(CITIES) >= 5
    assert "Madrid" in CITIES
    assert "Barcelona" in CITIES


def test_cabin_classes_list_is_complete():
    """Test CABIN_CLASSES has all standard classes."""
    # Arrange
    expected_classes = ["economy", "business", "first class"]

    # Assert
    for cabin_class in expected_classes:
        assert cabin_class in CABIN_CLASSES


def test_create_empty_flight_context():
    """Test creating empty flight context."""
    # Act
    context = create_empty_flight_context()

    # Assert
    assert isinstance(context, ConversationContext)
    assert len(context.history.messages) == 0
    assert len(context.current_slots) == 0
    assert context.current_flow == "none"
    assert "origin" in context.expected_slots


def test_create_context_after_origin():
    """Test creating context after origin is provided."""
    # Act
    context = create_context_after_origin(origin="Paris")

    # Assert
    assert isinstance(context, ConversationContext)
    assert len(context.history.messages) == 2
    assert context.current_slots["origin"] == "Paris"
    assert context.current_flow == "book_flight"
    assert "destination" in context.expected_slots


def test_create_context_after_origin_destination():
    """Test creating context after origin and destination are provided."""
    # Act
    context = create_context_after_origin_destination(
        origin="London",
        destination="New York"
    )

    # Assert
    assert isinstance(context, ConversationContext)
    assert context.current_slots["origin"] == "London"
    assert context.current_slots["destination"] == "New York"
    assert context.current_flow == "book_flight"
    assert "departure_date" in context.expected_slots


def test_create_context_before_confirmation():
    """Test creating context with all slots filled."""
    # Act
    context = create_context_before_confirmation(
        origin="Tokyo",
        destination="Paris",
        departure_date="next Monday"
    )

    # Assert
    assert isinstance(context, ConversationContext)
    assert context.current_slots["origin"] == "Tokyo"
    assert context.current_slots["destination"] == "Paris"
    assert context.current_slots["departure_date"] == "next Monday"
    assert len(context.expected_slots) == 0  # All filled


def test_helper_functions_use_defaults():
    """Test helper functions work with default values."""
    # Act
    context1 = create_context_after_origin()
    context2 = create_context_after_origin_destination()
    context3 = create_context_before_confirmation()

    # Assert - should not raise and should have sensible defaults
    assert context1.current_slots["origin"] == "Madrid"
    assert context2.current_slots["destination"] == "Barcelona"
    assert context3.current_slots["departure_date"] == "tomorrow"
```

**Verify tests fail:**
```bash
uv run pytest tests/unit/test_dataset_domains.py -v
# Expected: FAILED (module not implemented yet)
```

**Commit:**
```bash
git add tests/
git commit -m "test: add failing tests for flight booking domain"
```

#### Green Phase: Make Tests Pass

Implement the code as specified in "Implementación Detallada" section.

**Verify tests pass:**
```bash
uv run pytest tests/unit/test_dataset_domains.py -v
# Expected: PASSED ✅
```

**Commit:**
```bash
git add src/ tests/
git commit -m "feat: implement flight booking domain configuration"
```

#### Refactor Phase: Improve Design

- Add more city variations
- Add more utterance variations
- Ensure all docstrings are complete
- Tests must still pass!

**Commit:**
```bash
git add src/
git commit -m "refactor: expand flight booking domain with more variations"
```

### Criterios de Éxito

- [ ] `FLIGHT_BOOKING` domain configuration is complete
- [ ] All required slots, flows, and actions defined
- [ ] Example data provides sufficient variety
- [ ] Helper functions create valid contexts
- [ ] All tests pass
- [ ] Mypy passes with no errors
- [ ] Ruff passes with no errors
- [ ] Can be imported: `from soni.dataset.domains import FLIGHT_BOOKING`

### Validación Manual

**Comandos para validar:**

```bash
# Type checking
uv run mypy src/soni/dataset/domains/

# Tests
uv run pytest tests/unit/test_dataset_domains.py -v

# Linting
uv run ruff check src/soni/dataset/domains/
uv run ruff format src/soni/dataset/domains/

# Quick import test
uv run python -c "from soni.dataset.domains import FLIGHT_BOOKING; print(FLIGHT_BOOKING.name)"
```

**Resultado esperado:**
- All tests pass
- No mypy errors
- No ruff errors
- Domain can be imported and used

### Referencias

- docs/design/10-dsl-specification/ - DSL specification
- examples/flight_booking/soni.yaml - Flight booking example configuration
- docs/design/06-nlu-system.md - NLU system design

### Notas Adicionales

- This domain serves as the template for other domains (hotel, restaurant, ecommerce)
- Helper functions reduce boilerplate in pattern generators
- Example data should have variety but remain realistic
- All constants should be easily extendable
