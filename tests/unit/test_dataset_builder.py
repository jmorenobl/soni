"""Unit tests for DatasetBuilder."""

import dspy
import pytest

from soni.dataset.base import ConversationContext, DomainConfig, ExampleTemplate, PatternGenerator
from soni.dataset.builder import DatasetBuilder
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
    # Auto-discovers all patterns and domains
    assert len(builder.pattern_generators) > 0
    assert len(builder.domain_configs) > 0


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
    # Builder auto-discovers, so we check it has patterns and domains
    initial_patterns = len(builder.pattern_generators)
    initial_domains = len(builder.domain_configs)

    # Act
    stats = builder.get_stats()

    # Assert
    assert stats["patterns"] == initial_patterns
    assert stats["domains"] == initial_domains
    assert stats["contexts"] == 2
    assert stats["max_combinations"] == initial_patterns * initial_domains * 2


def test_build_all():
    """Test build_all generates examples for all registered patterns and domains."""
    # Arrange
    builder = DatasetBuilder()
    # Builder auto-discovers all patterns and domains

    # Act
    examples = builder.build_all(examples_per_combination=1)

    # Assert
    # Should generate examples from all patterns and domains
    assert len(examples) > 0
    assert all(isinstance(ex, dspy.Example) for ex in examples)
