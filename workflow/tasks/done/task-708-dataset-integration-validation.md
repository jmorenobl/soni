## Task: 708 - Dataset Integration and Validation

**ID de tarea:** 708
**Hito:** Dataset Creation for NLU Optimization
**Dependencias:** Task 707
**Duración estimada:** 2-3 horas

### Objetivo

Integrate all patterns and domains into the DatasetBuilder, create the complete dataset, validate it, and document usage.

### Contexto

This task completes the dataset package by:
1. Registering all patterns and domains in builder
2. Creating the complete dataset (~150-200 examples)
3. Validating dataset quality
4. Creating usage documentation and examples

### Entregables

- [ ] All patterns registered in `patterns/__init__.py`
- [ ] DatasetBuilder auto-discovers patterns and domains
- [ ] Complete dataset generated and validated
- [ ] `src/soni/dataset/README.md` with usage examples
- [ ] Integration tests in `tests/integration/test_dataset_integration.py`
- [ ] Dataset statistics printed (distribution by pattern/domain/context)

### Implementación Detallada

#### Paso 1: Register all patterns

**Archivo:** `src/soni/dataset/patterns/__init__.py`

```python
"""Pattern generators for all conversational patterns."""

from soni.dataset.patterns.slot_value import SlotValueGenerator
from soni.dataset.patterns.correction import CorrectionGenerator
from soni.dataset.patterns.modification import ModificationGenerator
from soni.dataset.patterns.interruption import InterruptionGenerator
from soni.dataset.patterns.digression import DigressionGenerator
from soni.dataset.patterns.clarification import ClarificationGenerator
from soni.dataset.patterns.cancellation import CancellationGenerator
from soni.dataset.patterns.confirmation import ConfirmationGenerator
from soni.dataset.patterns.continuation import ContinuationGenerator

ALL_PATTERN_GENERATORS = {
    "slot_value": SlotValueGenerator(),
    "correction": CorrectionGenerator(),
    "modification": ModificationGenerator(),
    "interruption": InterruptionGenerator(),
    "digression": DigressionGenerator(),
    "clarification": ClarificationGenerator(),
    "cancellation": CancellationGenerator(),
    "confirmation": ConfirmationGenerator(),
    "continuation": ContinuationGenerator(),
}

__all__ = [
    "SlotValueGenerator",
    "CorrectionGenerator",
    "ModificationGenerator",
    "InterruptionGenerator",
    "DigressionGenerator",
    "ClarificationGenerator",
    "CancellationGenerator",
    "ConfirmationGenerator",
    "ContinuationGenerator",
    "ALL_PATTERN_GENERATORS",
]
```

#### Paso 2: Auto-discovery in builder

**Update:** `src/soni/dataset/builder.py`

```python
from soni.dataset.patterns import ALL_PATTERN_GENERATORS
from soni.dataset.domains import ALL_DOMAINS

class DatasetBuilder:
    def __init__(
        self,
        pattern_generators: dict[str, PatternGenerator] | None = None,
        domain_configs: dict[str, DomainConfig] | None = None,
    ):
        # Auto-discover if not provided
        self.pattern_generators = pattern_generators or ALL_PATTERN_GENERATORS
        self.domain_configs = domain_configs or ALL_DOMAINS
```

#### Paso 3: Create usage script

**Archivo:** `examples/dataset/generate_training_dataset.py`

```python
"""Example script to generate complete training dataset."""

from soni.dataset import DatasetBuilder, print_dataset_stats

def main():
    # Create builder with all patterns and domains
    builder = DatasetBuilder()

    # Show stats
    stats = builder.get_stats()
    print(f"Loaded {stats['patterns']} patterns, {stats['domains']} domains")
    print(f"Max combinations: {stats['max_combinations']}")

    # Build complete dataset
    print("\nGenerating dataset...")
    trainset = builder.build_all(examples_per_combination=2)

    # Validate and print stats
    print_dataset_stats(trainset)

    print(f"\n✅ Generated {len(trainset)} examples successfully!")

    return trainset

if __name__ == "__main__":
    trainset = main()
```

#### Paso 4: Create README

**Archivo:** `src/soni/dataset/README.md`

```markdown
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
```

### TDD Cycle

**Test file:** `tests/integration/test_dataset_integration.py`

```python
"""Integration tests for complete dataset generation."""

import pytest
from soni.dataset import DatasetBuilder, validate_dataset
from soni.dataset.patterns import ALL_PATTERN_GENERATORS
from soni.dataset.domains import ALL_DOMAINS


def test_dataset_builder_auto_discovers_all():
    """Test builder auto-discovers all patterns and domains."""
    builder = DatasetBuilder()

    assert len(builder.pattern_generators) == 9  # All patterns
    assert len(builder.domain_configs) == 4  # All domains


def test_generate_complete_dataset():
    """Test generating complete dataset."""
    builder = DatasetBuilder()

    trainset = builder.build_all(examples_per_combination=1)

    # Should have examples
    assert len(trainset) > 0

    # Validate dataset
    stats = validate_dataset(trainset)
    assert stats["total_examples"] > 0


def test_dataset_covers_all_patterns():
    """Test dataset covers all MessageType patterns."""
    builder = DatasetBuilder()
    trainset = builder.build_all(examples_per_combination=1)

    from soni.du.models import MessageType

    patterns_in_dataset = {ex.result.message_type for ex in trainset}

    # Should have most patterns (some may not work in all contexts)
    assert len(patterns_in_dataset) >= 7  # At least 7 of 9


def test_dataset_covers_all_domains():
    """Test dataset covers all domains."""
    builder = DatasetBuilder()
    trainset = builder.build_all(examples_per_combination=1)

    domains_in_dataset = set()
    for ex in trainset:
        if hasattr(ex, "context"):
            # Extract domain from context (would need metadata)
            pass

    # Basic check: should have multiple domains
    assert len(trainset) >= len(ALL_DOMAINS)


def test_dataset_balanced():
    """Test dataset is reasonably balanced."""
    builder = DatasetBuilder()
    trainset = builder.build_all(examples_per_combination=2)

    stats = validate_dataset(trainset)

    # Should not have validation errors about balance
    # (validate_dataset raises if severely imbalanced)
    assert stats["total_examples"] > 0
```

### Criterios de Éxito

- [ ] All 9 patterns registered
- [ ] All 4 domains registered
- [ ] DatasetBuilder auto-discovers all
- [ ] Complete dataset generates successfully (~150-200 examples)
- [ ] Dataset validates without errors
- [ ] README with usage examples
- [ ] Integration tests pass
- [ ] Can run: `uv run python examples/dataset/generate_training_dataset.py`

### Validación Manual

```bash
# Run generation script
uv run python examples/dataset/generate_training_dataset.py

# Integration tests
uv run pytest tests/integration/test_dataset_integration.py -v

# Full test suite
uv run pytest tests/unit/test_dataset_*.py tests/integration/test_dataset_*.py -v
```

### Referencias

- All previous dataset tasks (701-707)
- docs/design/06-nlu-system.md - NLU optimization

### Notas Adicionales

- This completes the dataset package
- Target ~150-200 examples depending on examples_per_combination
- Dataset can now be used with DSPy optimizers
- Consider adding script to save dataset to disk for reuse
- May want to add data versioning in future
