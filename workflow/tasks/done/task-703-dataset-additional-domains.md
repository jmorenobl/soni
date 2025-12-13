## Task: 703 - Dataset Additional Domains (Hotel, Restaurant, Ecommerce)

**ID de tarea:** 703
**Hito:** Dataset Creation for NLU Optimization
**Dependencias:** Task 702 (Flight Booking Domain)
**Duración estimada:** 4-5 horas

### Objetivo

Implement three additional business domains (hotel booking, restaurant reservation, ecommerce) following the same pattern as flight_booking, providing diversity for training the NLU system across different contexts.

### Contexto

To ensure the NLU system generalizes well across different business domains, we need training examples from multiple contexts. These three domains provide complementary slot types and conversation patterns:

- **Hotel Booking**: Location-based with dates (checkin/checkout)
- **Restaurant**: Location, time, party size (different slot types than flights)
- **Ecommerce**: Product search, quantity, shipping (transactional domain)

Each domain follows the same structure as `flight_booking.py` for consistency.

### Entregables

- [ ] `src/soni/dataset/domains/hotel_booking.py` implemented
- [ ] `src/soni/dataset/domains/restaurant.py` implemented
- [ ] `src/soni/dataset/domains/ecommerce.py` implemented
- [ ] All domains have configuration + example data + helpers
- [ ] Domains registered in `domains/__init__.py`
- [ ] Unit tests extended in `tests/unit/test_dataset_domains.py`

### Implementación Detallada

#### Paso 1: Create hotel_booking.py

**Archivo:** `src/soni/dataset/domains/hotel_booking.py`

**Código específico:**

```python
"""Hotel booking domain configuration and example data."""

from soni.dataset.base import DomainConfig
import dspy
from soni.dataset.base import ConversationContext

# Domain configuration
HOTEL_BOOKING = DomainConfig(
    name="hotel_booking",
    description="Book hotel rooms in different cities",
    available_flows=[
        "book_hotel",
        "search_hotels",
        "check_reservation",
        "modify_reservation",
        "cancel_reservation",
    ],
    available_actions=[
        "search_hotels",
        "book_hotel",
        "modify_reservation",
        "cancel_reservation",
        "send_confirmation",
    ],
    slots={
        "location": "city",
        "checkin_date": "date",
        "checkout_date": "date",
        "guests": "number",
        "room_type": "string",
    },
    slot_prompts={
        "location": "Which city would you like to stay in?",
        "checkin_date": "When would you like to check in?",
        "checkout_date": "When would you like to check out?",
        "guests": "How many guests will be staying?",
        "room_type": "What type of room would you prefer? (single, double, suite)",
    },
)

# Example data
CITIES = [
    "Madrid",
    "Barcelona",
    "Paris",
    "London",
    "New York",
    "Tokyo",
    "Rome",
]

ROOM_TYPES = [
    "single",
    "double",
    "suite",
    "deluxe",
]

GUEST_COUNTS = [1, 2, 3, 4]

BOOKING_UTTERANCES = [
    "I want to book a hotel",
    "Book a hotel room",
    "I need a hotel reservation",
    "Can you help me book a hotel",
]


def create_empty_hotel_context() -> ConversationContext:
    """Create context for new hotel booking conversation."""
    return ConversationContext(
        history=dspy.History(messages=[]),
        current_slots={},
        current_flow="none",
        expected_slots=["location", "checkin_date", "checkout_date"],
    )


def create_context_after_location(location: str = "Barcelona") -> ConversationContext:
    """Create context after user provided location."""
    return ConversationContext(
        history=dspy.History(messages=[
            {
                "user_message": "I want to book a hotel",
                "result": {"command": "book_hotel", "message_type": "interruption"},
            },
            {
                "user_message": f"In {location}",
                "result": {
                    "command": "book_hotel",
                    "message_type": "slot_value",
                    "slots": [{"name": "location", "value": location}],
                },
            },
        ]),
        current_slots={"location": location},
        current_flow="book_hotel",
        expected_slots=["checkin_date", "checkout_date"],
    )
```

**Explicación:**
- Similar structure to flight_booking but with hotel-specific slots
- Different slot types: location instead of origin/destination
- Room types instead of cabin classes

#### Paso 2: Create restaurant.py

**Archivo:** `src/soni/dataset/domains/restaurant.py`

**Código específico:**

```python
"""Restaurant reservation domain configuration and example data."""

from soni.dataset.base import DomainConfig
import dspy
from soni.dataset.base import ConversationContext

# Domain configuration
RESTAURANT = DomainConfig(
    name="restaurant",
    description="Make restaurant reservations",
    available_flows=[
        "book_table",
        "search_restaurants",
        "check_reservation",
        "modify_reservation",
        "cancel_reservation",
    ],
    available_actions=[
        "search_restaurants",
        "book_table",
        "modify_reservation",
        "cancel_reservation",
        "send_confirmation",
    ],
    slots={
        "location": "city",
        "date": "date",
        "time": "time",
        "party_size": "number",
        "cuisine": "string",
    },
    slot_prompts={
        "location": "Which city are you looking for a restaurant in?",
        "date": "What date would you like to dine?",
        "time": "What time would you prefer?",
        "party_size": "How many people will be dining?",
        "cuisine": "What type of cuisine would you like?",
    },
)

# Example data
CITIES = [
    "Madrid",
    "Barcelona",
    "Paris",
    "London",
    "New York",
    "Tokyo",
]

CUISINES = [
    "Italian",
    "Japanese",
    "Spanish",
    "French",
    "Chinese",
    "Mexican",
]

TIMES = [
    "7:00 PM",
    "8:00 PM",
    "7:30 PM",
    "9:00 PM",
]

PARTY_SIZES = [2, 4, 6, 8]

BOOKING_UTTERANCES = [
    "I want to make a reservation",
    "Book a table",
    "I need a restaurant reservation",
    "Can you help me book a table",
]


def create_empty_restaurant_context() -> ConversationContext:
    """Create context for new restaurant reservation."""
    return ConversationContext(
        history=dspy.History(messages=[]),
        current_slots={},
        current_flow="none",
        expected_slots=["location", "date", "time", "party_size"],
    )


def create_context_after_location(location: str = "Madrid") -> ConversationContext:
    """Create context after user provided location."""
    return ConversationContext(
        history=dspy.History(messages=[
            {
                "user_message": "I want to book a table",
                "result": {"command": "book_table", "message_type": "interruption"},
            },
            {
                "user_message": f"In {location}",
                "result": {
                    "command": "book_table",
                    "message_type": "slot_value",
                    "slots": [{"name": "location", "value": location}],
                },
            },
        ]),
        current_slots={"location": location},
        current_flow="book_table",
        expected_slots=["date", "time", "party_size"],
    )
```

**Explicación:**
- Different slot types: time, party_size (not used in flights/hotels)
- Cuisine preference adds another dimension
- Shorter time horizon (same day bookings common)

#### Paso 3: Create ecommerce.py

**Archivo:** `src/soni/dataset/domains/ecommerce.py`

**Código específico:**

```python
"""E-commerce shopping domain configuration and example data."""

from soni.dataset.base import DomainConfig
import dspy
from soni.dataset.base import ConversationContext

# Domain configuration
ECOMMERCE = DomainConfig(
    name="ecommerce",
    description="Shop for products and manage orders",
    available_flows=[
        "search_product",
        "add_to_cart",
        "checkout",
        "track_order",
        "return_product",
    ],
    available_actions=[
        "search_products",
        "add_to_cart",
        "process_payment",
        "track_shipment",
        "initiate_return",
    ],
    slots={
        "product": "string",
        "quantity": "number",
        "color": "string",
        "size": "string",
        "shipping_address": "address",
    },
    slot_prompts={
        "product": "What product are you looking for?",
        "quantity": "How many would you like to order?",
        "color": "What color would you prefer?",
        "size": "What size do you need?",
        "shipping_address": "What's the shipping address?",
    },
)

# Example data
PRODUCTS = [
    "laptop",
    "phone",
    "headphones",
    "camera",
    "tablet",
    "smartwatch",
]

COLORS = [
    "black",
    "white",
    "silver",
    "blue",
    "red",
]

SIZES = [
    "small",
    "medium",
    "large",
    "XL",
]

QUANTITIES = [1, 2, 3, 5]

SEARCH_UTTERANCES = [
    "I'm looking for a",
    "Show me",
    "I want to buy a",
    "Can you help me find a",
]


def create_empty_shopping_context() -> ConversationContext:
    """Create context for new shopping session."""
    return ConversationContext(
        history=dspy.History(messages=[]),
        current_slots={},
        current_flow="none",
        expected_slots=["product", "quantity"],
    )


def create_context_after_product(product: str = "laptop") -> ConversationContext:
    """Create context after user specified product."""
    return ConversationContext(
        history=dspy.History(messages=[
            {
                "user_message": f"I want to buy a {product}",
                "result": {
                    "command": "search_product",
                    "message_type": "interruption",
                    "slots": [{"name": "product", "value": product}],
                },
            },
        ]),
        current_slots={"product": product},
        current_flow="search_product",
        expected_slots=["quantity", "color", "size"],
    )
```

**Explicación:**
- Transactional domain (different from booking domains)
- Product attributes (color, size) create variation
- Different flow: search → add to cart → checkout

#### Paso 4: Update domains/__init__.py

**Archivo:** `src/soni/dataset/domains/__init__.py`

**Código específico:**

```python
"""Domain configurations for dataset generation."""

from soni.dataset.domains.flight_booking import FLIGHT_BOOKING
from soni.dataset.domains.hotel_booking import HOTEL_BOOKING
from soni.dataset.domains.restaurant import RESTAURANT
from soni.dataset.domains.ecommerce import ECOMMERCE

# Registry of all available domains
ALL_DOMAINS = {
    "flight_booking": FLIGHT_BOOKING,
    "hotel_booking": HOTEL_BOOKING,
    "restaurant": RESTAURANT,
    "ecommerce": ECOMMERCE,
}

__all__ = [
    "FLIGHT_BOOKING",
    "HOTEL_BOOKING",
    "RESTAURANT",
    "ECOMMERCE",
    "ALL_DOMAINS",
]
```

### TDD Cycle (MANDATORY for new features)

#### Red Phase: Write Failing Tests

**Test file:** `tests/unit/test_dataset_domains.py` (extend existing)

**Agregar estos tests:**

```python
from soni.dataset.domains.hotel_booking import (
    HOTEL_BOOKING,
    create_empty_hotel_context,
    create_context_after_location as create_hotel_context_after_location,
)
from soni.dataset.domains.restaurant import (
    RESTAURANT,
    create_empty_restaurant_context,
    create_context_after_location as create_restaurant_context_after_location,
)
from soni.dataset.domains.ecommerce import (
    ECOMMERCE,
    create_empty_shopping_context,
    create_context_after_product,
)


# Hotel Booking Tests
def test_hotel_booking_domain_is_valid():
    """Test HOTEL_BOOKING domain configuration is valid."""
    assert isinstance(HOTEL_BOOKING, DomainConfig)
    assert HOTEL_BOOKING.name == "hotel_booking"
    assert "book_hotel" in HOTEL_BOOKING.available_flows


def test_hotel_booking_has_required_slots():
    """Test hotel booking has location and date slots."""
    required_slots = ["location", "checkin_date", "checkout_date"]
    for slot in required_slots:
        assert slot in HOTEL_BOOKING.slots


def test_create_empty_hotel_context():
    """Test creating empty hotel context."""
    context = create_empty_hotel_context()
    assert len(context.history.messages) == 0
    assert context.current_flow == "none"


def test_create_hotel_context_after_location():
    """Test creating hotel context after location."""
    context = create_hotel_context_after_location(location="Paris")
    assert context.current_slots["location"] == "Paris"
    assert context.current_flow == "book_hotel"


# Restaurant Tests
def test_restaurant_domain_is_valid():
    """Test RESTAURANT domain configuration is valid."""
    assert isinstance(RESTAURANT, DomainConfig)
    assert RESTAURANT.name == "restaurant"
    assert "book_table" in RESTAURANT.available_flows


def test_restaurant_has_required_slots():
    """Test restaurant has location, date, time, party_size slots."""
    required_slots = ["location", "date", "time", "party_size"]
    for slot in required_slots:
        assert slot in RESTAURANT.slots


def test_create_empty_restaurant_context():
    """Test creating empty restaurant context."""
    context = create_empty_restaurant_context()
    assert len(context.history.messages) == 0
    assert context.current_flow == "none"


def test_create_restaurant_context_after_location():
    """Test creating restaurant context after location."""
    context = create_restaurant_context_after_location(location="Tokyo")
    assert context.current_slots["location"] == "Tokyo"
    assert context.current_flow == "book_table"


# Ecommerce Tests
def test_ecommerce_domain_is_valid():
    """Test ECOMMERCE domain configuration is valid."""
    assert isinstance(ECOMMERCE, DomainConfig)
    assert ECOMMERCE.name == "ecommerce"
    assert "search_product" in ECOMMERCE.available_flows


def test_ecommerce_has_required_slots():
    """Test ecommerce has product and quantity slots."""
    required_slots = ["product", "quantity"]
    for slot in required_slots:
        assert slot in ECOMMERCE.slots


def test_create_empty_shopping_context():
    """Test creating empty shopping context."""
    context = create_empty_shopping_context()
    assert len(context.history.messages) == 0
    assert context.current_flow == "none"


def test_create_ecommerce_context_after_product():
    """Test creating ecommerce context after product selection."""
    context = create_context_after_product(product="camera")
    assert context.current_slots["product"] == "camera"
    assert context.current_flow == "search_product"


# Cross-domain Tests
def test_all_domains_are_importable():
    """Test all domains can be imported from registry."""
    from soni.dataset.domains import ALL_DOMAINS

    assert "flight_booking" in ALL_DOMAINS
    assert "hotel_booking" in ALL_DOMAINS
    assert "restaurant" in ALL_DOMAINS
    assert "ecommerce" in ALL_DOMAINS
    assert len(ALL_DOMAINS) == 4


def test_all_domains_have_unique_names():
    """Test all domains have unique names."""
    from soni.dataset.domains import ALL_DOMAINS

    names = [domain.name for domain in ALL_DOMAINS.values()]
    assert len(names) == len(set(names))  # No duplicates
```

**Verify tests fail:**
```bash
uv run pytest tests/unit/test_dataset_domains.py -v
# Expected: FAILED (modules not implemented yet)
```

**Commit:**
```bash
git add tests/
git commit -m "test: add failing tests for additional domains"
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
git commit -m "feat: implement hotel, restaurant, and ecommerce domains"
```

#### Refactor Phase: Improve Design

- Ensure consistent naming across domains
- Add more example data variations
- Complete all docstrings
- Tests must still pass!

**Commit:**
```bash
git add src/
git commit -m "refactor: improve additional domains with better consistency"
```

### Criterios de Éxito

- [ ] All three domains implemented following flight_booking pattern
- [ ] Each domain has complete configuration + example data + helpers
- [ ] All domains registered in ALL_DOMAINS registry
- [ ] All tests pass
- [ ] Mypy passes with no errors
- [ ] Ruff passes with no errors
- [ ] Can import all domains: `from soni.dataset.domains import ALL_DOMAINS`

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
uv run python -c "from soni.dataset.domains import ALL_DOMAINS; print(f'Loaded {len(ALL_DOMAINS)} domains')"
```

**Resultado esperado:**
- All tests pass
- No mypy or ruff errors
- 4 domains loaded successfully

### Referencias

- Task 702 - Flight Booking Domain (template)
- docs/design/10-dsl-specification/ - DSL patterns

### Notas Adicionales

- Each domain should be self-contained
- Follow same structure as flight_booking for consistency
- Different slot types provide variety for NLU training
- Helper functions make pattern generation easier
