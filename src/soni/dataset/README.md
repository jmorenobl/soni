# Soni Dataset Package

Training dataset generator for NLU optimization with DSPy.

## Overview

This package generates training examples by combining three dimensions:
- **9 Patterns**: Conversational patterns (SLOT_VALUE, CORRECTION, etc.)
- **4 Domains**: Business domains (flight_booking, hotel_booking, etc.)
- **2 Contexts**: Conversation contexts (cold_start, ongoing)

## Quick Start

```python
from soni.dataset import DatasetBuilder

# Create builder
builder = DatasetBuilder()

# Generate complete dataset
trainset = builder.build_all(examples_per_combination=2)
# Result: 9 × 4 × 2 × 2 = 144 examples (estimated)

print(f"Generated {len(trainset)} examples")
```

## Usage Examples

### Generate Specific Patterns

```python
# Only SLOT_VALUE and CORRECTION patterns
trainset = builder.build(
    patterns=["slot_value", "correction"],
    domains=None,  # All domains
    contexts=None,  # Both contexts
    examples_per_combination=3,
)
```

### Generate Specific Domains

```python
# Only flight and hotel booking
trainset = builder.build(
    patterns=None,  # All patterns
    domains=["flight_booking", "hotel_booking"],
    contexts=["ongoing"],  # Only ongoing
    examples_per_combination=2,
)
```

### Validate Dataset

```python
from soni.dataset import validate_dataset, print_dataset_stats

# Validate
stats = validate_dataset(trainset)

# Print readable stats
print_dataset_stats(trainset)
```

## Architecture

```
dataset/
├── base.py          # Core classes (DomainConfig, PatternGenerator, etc.)
├── builder.py       # DatasetBuilder (orchestrates generation)
├── registry.py      # Validation utilities
├── patterns/        # 9 pattern generators
│   ├── slot_value.py
│   ├── correction.py
│   └── ...
├── domains/         # 4 domain configurations
│   ├── flight_booking.py
│   ├── hotel_booking.py
│   └── ...
└── contexts/        # Context helpers
```

## Pattern Reference

| Pattern | Description | Contexts |
|---------|-------------|----------|
| SLOT_VALUE | Direct answer to prompt | Both |
| CORRECTION | Fixing mistake | Ongoing |
| MODIFICATION | Changing value | Ongoing |
| INTERRUPTION | Starting new task | Both |
| DIGRESSION | Off-topic question | Ongoing |
| CLARIFICATION | Asking why | Ongoing |
| CANCELLATION | Abandoning task | Ongoing |
| CONFIRMATION | Yes/no answer | Ongoing |
| CONTINUATION | General continuation | Ongoing |

## Domain Reference

- **flight_booking**: Origin, destination, dates, passengers
- **hotel_booking**: Location, check-in/out, guests, room type
- **restaurant**: Location, date, time, party size, cuisine
- **ecommerce**: Product, quantity, color, size

## Extending

### Add New Domain

```python
# src/soni/dataset/domains/car_rental.py
from soni.dataset.base import DomainConfig

CAR_RENTAL = DomainConfig(
    name="car_rental",
    description="Rent cars",
    available_flows=["rent_car"],
    available_actions=["search_cars"],
    slots={"location": "city", "pickup_date": "date"},
    slot_prompts={"location": "Where?", "pickup_date": "When?"},
)
```

Register in `domains/__init__.py`:
```python
from soni.dataset.domains.car_rental import CAR_RENTAL

ALL_DOMAINS["car_rental"] = CAR_RENTAL
```

### Add New Pattern

Implement `PatternGenerator` interface:

```python
from soni.dataset.base import PatternGenerator
from soni.du.models import MessageType

class MyPatternGenerator(PatternGenerator):
    @property
    def message_type(self) -> MessageType:
        return MessageType.MY_PATTERN

    def generate_examples(self, domain_config, context_type, count):
        # Generate examples
        return examples
```

Register in `patterns/__init__.py`.

## Testing

```bash
# Unit tests
uv run pytest tests/unit/test_dataset_*.py -v

# Integration test (full dataset generation)
uv run pytest tests/integration/test_dataset_integration.py -v
```
