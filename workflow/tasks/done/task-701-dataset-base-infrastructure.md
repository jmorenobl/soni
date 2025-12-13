## Task: 701 - Dataset Base Infrastructure

**ID de tarea:** 701
**Hito:** Dataset Creation for NLU Optimization
**Dependencias:** Ninguna
**Duración estimada:** 3-4 horas

### Objetivo

Create the foundational infrastructure for the dataset package, including base classes, type definitions, and the builder architecture that will enable systematic generation of training examples for DSPy optimization.

### Contexto

The NLU system currently operates in baseline mode without optimization. To optimize it using DSPy's MIPROv2, we need a comprehensive dataset with examples of all conversational patterns across multiple domains and contexts (with/without conversation history).

This task creates the core infrastructure that all subsequent tasks will build upon:
- Base classes for domain configuration and example generation
- Type-safe structures using Pydantic
- Builder pattern for composing examples from multiple dimensions (pattern × domain × context)

**Reference:** docs/design/06-nlu-system.md (DSPy Optimization section)

### Entregables

- [ ] `src/soni/dataset/` package created
- [ ] `base.py` with core classes: `DomainConfig`, `ConversationContext`, `ExampleTemplate`, `PatternGenerator`
- [ ] `builder.py` with `DatasetBuilder` class
- [ ] `registry.py` with validation utilities
- [ ] `__init__.py` with public API
- [ ] All classes have complete type hints and docstrings
- [ ] Unit tests in `tests/unit/test_dataset_base.py`

### Implementación Detallada

#### Paso 1: Create package structure

**Archivo(s) a crear:**
- `src/soni/dataset/__init__.py`
- `src/soni/dataset/base.py`
- `src/soni/dataset/builder.py`
- `src/soni/dataset/registry.py`
- `src/soni/dataset/patterns/__init__.py`
- `src/soni/dataset/domains/__init__.py`
- `src/soni/dataset/contexts/__init__.py`

**Código específico para `base.py`:**

```python
"""Base classes for dataset construction."""

from typing import Any, Literal
import dspy
from pydantic import BaseModel, Field
from soni.du.models import DialogueContext, NLUOutput, MessageType


class DomainConfig(BaseModel):
    """Configuration for a business domain (e.g., flight booking).

    Defines the available flows, actions, and slots for a specific domain.
    This allows pattern generators to create contextually appropriate examples.
    """

    name: str = Field(description="Domain identifier (e.g., 'flight_booking')")
    description: str = Field(description="Human-readable description")
    available_flows: list[str] = Field(description="Flow names available in this domain")
    available_actions: list[str] = Field(description="Action names available in this domain")
    slots: dict[str, str] = Field(description="Slot name -> slot type mapping")
    slot_prompts: dict[str, str] = Field(description="Slot name -> prompt text mapping")

    model_config = {"frozen": True}  # Immutable


class ConversationContext(BaseModel):
    """Context for a conversation at a specific point in time.

    Captures the state of the conversation including history, current slots,
    active flow, and what slots are expected next.
    """

    history: dspy.History = Field(description="Conversation history")
    current_slots: dict[str, Any] = Field(
        default_factory=dict,
        description="Slots already filled in current flow"
    )
    current_flow: str = Field(
        default="none",
        description="Currently active flow name"
    )
    expected_slots: list[str] = Field(
        default_factory=list,
        description="Slot names expected to be filled next"
    )


class ExampleTemplate(BaseModel):
    """Template for creating a dspy.Example.

    This is an intermediate representation that can be converted to a
    dspy.Example with all the required fields properly structured.
    """

    user_message: str = Field(description="User's input message")
    conversation_context: ConversationContext = Field(description="Conversation state")
    expected_output: NLUOutput = Field(description="Expected NLU analysis")
    domain: str = Field(description="Domain name this example belongs to")
    pattern: str = Field(description="Pattern name this example demonstrates")
    context_type: Literal["cold_start", "ongoing"] = Field(
        description="Whether conversation has history"
    )
    current_datetime: str = Field(
        default="",
        description="Current datetime in ISO format"
    )

    def to_dspy_example(self, domain_config: DomainConfig) -> dspy.Example:
        """Convert to dspy.Example with proper format for optimization.

        Args:
            domain_config: Domain configuration to populate context

        Returns:
            dspy.Example ready for training/optimization
        """
        dialogue_context = DialogueContext(
            current_slots=self.conversation_context.current_slots,
            available_actions=domain_config.available_actions,
            available_flows=domain_config.available_flows,
            current_flow=self.conversation_context.current_flow,
            expected_slots=self.conversation_context.expected_slots,
        )

        return dspy.Example(
            user_message=self.user_message,
            history=self.conversation_context.history,
            context=dialogue_context,
            current_datetime=self.current_datetime,
            result=self.expected_output,
        ).with_inputs("user_message", "history", "context", "current_datetime")


class PatternGenerator:
    """Base class for pattern-specific example generators.

    Each subclass implements generation logic for a specific MessageType pattern
    (e.g., SLOT_VALUE, CORRECTION, INTERRUPTION).
    """

    @property
    def message_type(self) -> MessageType:
        """The MessageType this generator produces."""
        raise NotImplementedError("Subclasses must implement message_type property")

    def generate_examples(
        self,
        domain_config: DomainConfig,
        context_type: Literal["cold_start", "ongoing"],
        count: int = 3,
    ) -> list[ExampleTemplate]:
        """Generate N examples for this pattern + domain + context combination.

        Args:
            domain_config: Domain configuration
            context_type: "cold_start" (no history) or "ongoing" (with history)
            count: Number of examples to generate

        Returns:
            List of example templates
        """
        raise NotImplementedError("Subclasses must implement generate_examples()")
```

**Explicación:**
- `DomainConfig`: Immutable configuration for each business domain
- `ConversationContext`: Captures conversation state at any point
- `ExampleTemplate`: Intermediate format that converts to `dspy.Example`
- `PatternGenerator`: Abstract base for pattern-specific generators
- All classes use Pydantic for validation and type safety
- Follows SOLID principles: SRP, OCP, LSP, DIP

#### Paso 2: Create DatasetBuilder

**Archivo:** `src/soni/dataset/builder.py`

**Código específico:**

```python
"""Dataset builder - combines patterns, domains, and contexts."""

import dspy
from typing import Literal
from soni.dataset.base import PatternGenerator, DomainConfig


class DatasetBuilder:
    """Builds training datasets by combining patterns, domains, and contexts.

    This class orchestrates the generation of examples by combining:
    - Patterns: 9 conversational patterns (SLOT_VALUE, CORRECTION, etc.)
    - Domains: 4+ business domains (flight_booking, hotel_booking, etc.)
    - Contexts: 2 context types (cold_start, ongoing)

    Example:
        builder = DatasetBuilder()
        trainset = builder.build(
            patterns=["slot_value", "correction"],
            domains=["flight_booking", "hotel_booking"],
            contexts=["ongoing"],
            examples_per_combination=2,
        )
        # Result: 2 patterns × 2 domains × 1 context × 2 examples = 8 examples
    """

    def __init__(
        self,
        pattern_generators: dict[str, PatternGenerator] | None = None,
        domain_configs: dict[str, DomainConfig] | None = None,
    ):
        """Initialize builder with registries.

        Args:
            pattern_generators: Registry of pattern generators (default: auto-discover)
            domain_configs: Registry of domain configs (default: auto-discover)
        """
        self.pattern_generators = pattern_generators or {}
        self.domain_configs = domain_configs or {}

    def register_pattern(self, name: str, generator: PatternGenerator) -> None:
        """Register a pattern generator.

        Args:
            name: Pattern identifier (e.g., "slot_value")
            generator: Pattern generator instance
        """
        self.pattern_generators[name] = generator

    def register_domain(self, config: DomainConfig) -> None:
        """Register a domain configuration.

        Args:
            config: Domain configuration
        """
        self.domain_configs[config.name] = config

    def build(
        self,
        patterns: list[str] | None = None,
        domains: list[str] | None = None,
        contexts: list[Literal["cold_start", "ongoing"]] | None = None,
        examples_per_combination: int = 2,
    ) -> list[dspy.Example]:
        """Build dataset from specified dimensions.

        Args:
            patterns: List of pattern names (default: all registered)
            domains: List of domain names (default: all registered)
            contexts: List of context types (default: both)
            examples_per_combination: Examples per (pattern × domain × context)

        Returns:
            List of dspy.Example ready for optimization

        Raises:
            ValueError: If requested pattern/domain not registered
        """
        patterns = patterns or list(self.pattern_generators.keys())
        domains = domains or list(self.domain_configs.keys())
        contexts = contexts or ["cold_start", "ongoing"]

        # Validate all requested patterns and domains are registered
        for pattern in patterns:
            if pattern not in self.pattern_generators:
                raise ValueError(f"Pattern '{pattern}' not registered")

        for domain in domains:
            if domain not in self.domain_configs:
                raise ValueError(f"Domain '{domain}' not registered")

        all_examples: list[dspy.Example] = []

        # Generate all combinations
        for pattern_name in patterns:
            for domain_name in domains:
                for context_type in contexts:
                    generator = self.pattern_generators[pattern_name]
                    domain_config = self.domain_configs[domain_name]

                    # Generate templates
                    templates = generator.generate_examples(
                        domain_config=domain_config,
                        context_type=context_type,
                        count=examples_per_combination,
                    )

                    # Convert to dspy.Example
                    examples = [
                        template.to_dspy_example(domain_config)
                        for template in templates
                    ]

                    all_examples.extend(examples)

        return all_examples

    def build_all(self, examples_per_combination: int = 2) -> list[dspy.Example]:
        """Build complete dataset with all registered patterns, domains, and contexts.

        Args:
            examples_per_combination: Examples per (pattern × domain × context)

        Returns:
            Complete training dataset
        """
        return self.build(
            patterns=None,
            domains=None,
            contexts=None,
            examples_per_combination=examples_per_combination,
        )

    def get_stats(self) -> dict[str, int]:
        """Get statistics about registered generators and domains.

        Returns:
            Dictionary with counts of patterns, domains, and estimated examples
        """
        num_patterns = len(self.pattern_generators)
        num_domains = len(self.domain_configs)
        num_contexts = 2  # cold_start, ongoing

        return {
            "patterns": num_patterns,
            "domains": num_domains,
            "contexts": num_contexts,
            "max_combinations": num_patterns * num_domains * num_contexts,
        }
```

**Explicación:**
- Builder pattern for composing examples from multiple dimensions
- Registry-based: patterns and domains can be registered dynamically
- Validates all requested patterns/domains are available
- Generates all combinations: pattern × domain × context
- Provides statistics about available generators

#### Paso 3: Create Registry utilities

**Archivo:** `src/soni/dataset/registry.py`

**Código específico:**

```python
"""Registry and validation utilities for dataset creation."""

import dspy
from collections import Counter
from typing import Any
from soni.du.models import MessageType


def validate_dataset(examples: list[dspy.Example]) -> dict[str, Any]:
    """Validate a dataset and return statistics.

    Checks:
    - All examples have required fields
    - Examples are properly formatted
    - Distribution of patterns, domains, contexts

    Args:
        examples: List of dspy.Example instances

    Returns:
        Dictionary with validation results and statistics

    Raises:
        ValueError: If validation fails
    """
    if not examples:
        raise ValueError("Dataset is empty")

    stats = {
        "total_examples": len(examples),
        "patterns": Counter(),
        "domains": Counter(),
        "contexts": Counter(),
        "validation_errors": [],
    }

    for idx, example in enumerate(examples):
        # Check required fields
        required_fields = ["user_message", "history", "context", "result"]
        for field in required_fields:
            if not hasattr(example, field):
                stats["validation_errors"].append(
                    f"Example {idx}: missing field '{field}'"
                )

        # Collect statistics
        if hasattr(example, "result"):
            result = example.result
            if hasattr(result, "message_type"):
                stats["patterns"][result.message_type] += 1

    # Check distribution balance
    if stats["patterns"]:
        pattern_counts = list(stats["patterns"].values())
        min_count = min(pattern_counts)
        max_count = max(pattern_counts)

        # Warn if imbalanced (max > 3 * min)
        if max_count > 3 * min_count:
            stats["validation_errors"].append(
                f"Imbalanced pattern distribution: min={min_count}, max={max_count}"
            )

    if stats["validation_errors"]:
        raise ValueError(
            f"Dataset validation failed with {len(stats['validation_errors'])} errors: "
            f"{stats['validation_errors'][:3]}"
        )

    return stats


def print_dataset_stats(examples: list[dspy.Example]) -> None:
    """Print human-readable dataset statistics.

    Args:
        examples: List of dspy.Example instances
    """
    stats = validate_dataset(examples)

    print(f"\n=== Dataset Statistics ===")
    print(f"Total examples: {stats['total_examples']}")
    print(f"\nPattern distribution:")
    for pattern, count in sorted(stats['patterns'].items()):
        percentage = (count / stats['total_examples']) * 100
        print(f"  {pattern}: {count} ({percentage:.1f}%)")
```

**Explicación:**
- Validates dataset has all required fields
- Checks for balanced distribution across patterns
- Provides detailed statistics
- Raises errors if dataset is malformed

#### Paso 4: Create public API

**Archivo:** `src/soni/dataset/__init__.py`

**Código específico:**

```python
"""Public API for dataset creation.

This module provides the infrastructure for creating training datasets
for DSPy NLU optimization. It combines conversational patterns, business
domains, and conversation contexts to generate comprehensive examples.

Usage:
    from soni.dataset import DatasetBuilder

    builder = DatasetBuilder()
    trainset = builder.build_all(examples_per_combination=2)
"""

from soni.dataset.base import (
    DomainConfig,
    ConversationContext,
    ExampleTemplate,
    PatternGenerator,
)
from soni.dataset.builder import DatasetBuilder
from soni.dataset.registry import validate_dataset, print_dataset_stats

__all__ = [
    "DatasetBuilder",
    "DomainConfig",
    "ConversationContext",
    "ExampleTemplate",
    "PatternGenerator",
    "validate_dataset",
    "print_dataset_stats",
]
```

### TDD Cycle (MANDATORY for new features)

#### Red Phase: Write Failing Tests

**Test file:** `tests/unit/test_dataset_base.py`

**Failing tests to write FIRST:**

```python
"""Unit tests for dataset base classes."""

import pytest
import dspy
from soni.dataset.base import (
    DomainConfig,
    ConversationContext,
    ExampleTemplate,
    PatternGenerator,
)
from soni.du.models import MessageType, NLUOutput, SlotValue, DialogueContext


def test_domain_config_creation():
    """Test DomainConfig can be created with valid data."""
    # Arrange & Act
    config = DomainConfig(
        name="test_domain",
        description="Test domain",
        available_flows=["flow1"],
        available_actions=["action1"],
        slots={"slot1": "string"},
        slot_prompts={"slot1": "What is slot1?"},
    )

    # Assert
    assert config.name == "test_domain"
    assert "flow1" in config.available_flows
    assert config.slots["slot1"] == "string"


def test_domain_config_is_immutable():
    """Test DomainConfig is frozen (immutable)."""
    # Arrange
    config = DomainConfig(
        name="test",
        description="Test",
        available_flows=[],
        available_actions=[],
        slots={},
        slot_prompts={},
    )

    # Act & Assert
    with pytest.raises(Exception):  # Pydantic raises ValidationError for frozen models
        config.name = "new_name"


def test_conversation_context_creation():
    """Test ConversationContext can be created."""
    # Arrange & Act
    context = ConversationContext(
        history=dspy.History(messages=[]),
        current_slots={"origin": "Madrid"},
        current_flow="book_flight",
        expected_slots=["destination"],
    )

    # Assert
    assert context.current_flow == "book_flight"
    assert context.current_slots["origin"] == "Madrid"
    assert "destination" in context.expected_slots


def test_example_template_to_dspy_example():
    """Test ExampleTemplate converts to dspy.Example correctly."""
    # Arrange
    domain_config = DomainConfig(
        name="test_domain",
        description="Test",
        available_flows=["book_flight"],
        available_actions=["search_flights"],
        slots={"origin": "city"},
        slot_prompts={"origin": "Which city?"},
    )

    template = ExampleTemplate(
        user_message="Madrid",
        conversation_context=ConversationContext(
            history=dspy.History(messages=[]),
            current_slots={},
            current_flow="book_flight",
            expected_slots=["origin"],
        ),
        expected_output=NLUOutput(
            message_type=MessageType.SLOT_VALUE,
            command="book_flight",
            slots=[SlotValue(name="origin", value="Madrid", confidence=0.9)],
            confidence=0.9,
            reasoning="User provides origin",
        ),
        domain="test_domain",
        pattern="slot_value",
        context_type="ongoing",
    )

    # Act
    example = template.to_dspy_example(domain_config)

    # Assert
    assert isinstance(example, dspy.Example)
    assert example.user_message == "Madrid"
    assert hasattr(example, "history")
    assert hasattr(example, "context")
    assert hasattr(example, "result")
    assert example.result.command == "book_flight"


def test_pattern_generator_must_implement_abstract_methods():
    """Test PatternGenerator is abstract and requires implementation."""
    # Arrange
    generator = PatternGenerator()

    # Act & Assert - must raise NotImplementedError
    with pytest.raises(NotImplementedError):
        _ = generator.message_type

    with pytest.raises(NotImplementedError):
        generator.generate_examples(
            domain_config=DomainConfig(
                name="test",
                description="Test",
                available_flows=[],
                available_actions=[],
                slots={},
                slot_prompts={},
            ),
            context_type="ongoing",
            count=1,
        )
```

**Test file:** `tests/unit/test_dataset_builder.py`

```python
"""Unit tests for DatasetBuilder."""

import pytest
import dspy
from soni.dataset.builder import DatasetBuilder
from soni.dataset.base import PatternGenerator, DomainConfig, ExampleTemplate
from soni.du.models import MessageType, NLUOutput


class MockPatternGenerator(PatternGenerator):
    """Mock pattern generator for testing."""

    @property
    def message_type(self) -> MessageType:
        return MessageType.SLOT_VALUE

    def generate_examples(self, domain_config, context_type, count=3):
        return [
            ExampleTemplate(
                user_message="test",
                conversation_context=ConversationContext(
                    history=dspy.History(messages=[]),
                    current_slots={},
                    current_flow="none",
                    expected_slots=[],
                ),
                expected_output=NLUOutput(
                    message_type=MessageType.SLOT_VALUE,
                    command="test",
                    slots=[],
                    confidence=0.9,
                    reasoning="Test",
                ),
                domain=domain_config.name,
                pattern="slot_value",
                context_type=context_type,
            )
            for _ in range(count)
        ]


def test_dataset_builder_initialization():
    """Test DatasetBuilder can be initialized."""
    # Act
    builder = DatasetBuilder()

    # Assert
    assert isinstance(builder, DatasetBuilder)
    assert len(builder.pattern_generators) == 0
    assert len(builder.domain_configs) == 0


def test_register_pattern():
    """Test pattern registration."""
    # Arrange
    builder = DatasetBuilder()
    generator = MockPatternGenerator()

    # Act
    builder.register_pattern("test_pattern", generator)

    # Assert
    assert "test_pattern" in builder.pattern_generators
    assert builder.pattern_generators["test_pattern"] is generator


def test_register_domain():
    """Test domain registration."""
    # Arrange
    builder = DatasetBuilder()
    config = DomainConfig(
        name="test_domain",
        description="Test",
        available_flows=[],
        available_actions=[],
        slots={},
        slot_prompts={},
    )

    # Act
    builder.register_domain(config)

    # Assert
    assert "test_domain" in builder.domain_configs
    assert builder.domain_configs["test_domain"] is config


def test_build_raises_error_for_unregistered_pattern():
    """Test build raises ValueError for unregistered pattern."""
    # Arrange
    builder = DatasetBuilder()

    # Act & Assert
    with pytest.raises(ValueError, match="Pattern 'nonexistent' not registered"):
        builder.build(patterns=["nonexistent"])


def test_build_raises_error_for_unregistered_domain():
    """Test build raises ValueError for unregistered domain."""
    # Arrange
    builder = DatasetBuilder()

    # Act & Assert
    with pytest.raises(ValueError, match="Domain 'nonexistent' not registered"):
        builder.build(domains=["nonexistent"])


def test_build_generates_correct_number_of_examples():
    """Test build generates correct number of examples."""
    # Arrange
    builder = DatasetBuilder()
    builder.register_pattern("slot_value", MockPatternGenerator())
    builder.register_domain(
        DomainConfig(
            name="test_domain",
            description="Test",
            available_flows=[],
            available_actions=[],
            slots={},
            slot_prompts={},
        )
    )

    # Act
    # 1 pattern × 1 domain × 2 contexts × 3 examples = 6 examples
    examples = builder.build(
        patterns=["slot_value"],
        domains=["test_domain"],
        contexts=["cold_start", "ongoing"],
        examples_per_combination=3,
    )

    # Assert
    assert len(examples) == 6
    assert all(isinstance(ex, dspy.Example) for ex in examples)


def test_get_stats():
    """Test get_stats returns correct statistics."""
    # Arrange
    builder = DatasetBuilder()
    builder.register_pattern("pattern1", MockPatternGenerator())
    builder.register_pattern("pattern2", MockPatternGenerator())
    builder.register_domain(
        DomainConfig(
            name="domain1",
            description="Test",
            available_flows=[],
            available_actions=[],
            slots={},
            slot_prompts={},
        )
    )

    # Act
    stats = builder.get_stats()

    # Assert
    assert stats["patterns"] == 2
    assert stats["domains"] == 1
    assert stats["contexts"] == 2
    assert stats["max_combinations"] == 4  # 2 × 1 × 2
```

**Verify tests fail:**
```bash
uv run pytest tests/unit/test_dataset_base.py -v
uv run pytest tests/unit/test_dataset_builder.py -v
# Expected: FAILED (modules not implemented yet)
```

**Commit:**
```bash
git add tests/
git commit -m "test: add failing tests for dataset base infrastructure"
```

#### Green Phase: Make Tests Pass

Implement the code as specified in "Implementación Detallada" section.

**Verify tests pass:**
```bash
uv run pytest tests/unit/test_dataset_base.py -v
uv run pytest tests/unit/test_dataset_builder.py -v
# Expected: PASSED ✅
```

**Commit:**
```bash
git add src/ tests/
git commit -m "feat: implement dataset base infrastructure"
```

#### Refactor Phase: Improve Design

- Add comprehensive docstrings to all classes and methods
- Ensure all type hints are complete
- Add validation for edge cases
- Tests must still pass!

**Commit:**
```bash
git add src/
git commit -m "refactor: improve dataset base implementation with better docs"
```

### Criterios de Éxito

- [ ] All base classes implemented with complete type hints
- [ ] DatasetBuilder works with mock generators
- [ ] Validation utilities detect malformed datasets
- [ ] All tests pass (`uv run pytest tests/unit/test_dataset_*.py -v`)
- [ ] Mypy passes with no errors
- [ ] Ruff passes with no errors
- [ ] Code coverage >90% for dataset package
- [ ] Documentation is clear and complete

### Validación Manual

**Comandos para validar:**

```bash
# Type checking
uv run mypy src/soni/dataset/

# Tests
uv run pytest tests/unit/test_dataset_base.py -v
uv run pytest tests/unit/test_dataset_builder.py -v

# Linting
uv run ruff check src/soni/dataset/
uv run ruff format src/soni/dataset/

# Coverage
uv run pytest tests/unit/test_dataset_*.py --cov=src/soni/dataset --cov-report=term-missing
```

**Resultado esperado:**
- Mypy shows no errors
- All tests pass
- Ruff shows no linting errors
- Coverage >90%
- Package can be imported: `from soni.dataset import DatasetBuilder`

### Referencias

- docs/design/06-nlu-system.md - NLU system architecture
- docs/design/09-dspy-optimization.md - DSPy optimization patterns
- https://dspy-docs.vercel.app/ - DSPy documentation

### Notas Adicionales

- This is foundational infrastructure - must be solid before building patterns/domains
- All subsequent tasks (702-715) depend on this
- Keep classes small and focused (SRP)
- Use Pydantic for all data models
- Ensure immutability where appropriate (DomainConfig)
- Follow existing project patterns for type hints and documentation
