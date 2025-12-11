"""Unit tests for dataset base classes."""

import dspy
import pytest
from pydantic import ValidationError

from soni.dataset.base import (
    ConversationContext,
    DomainConfig,
    ExampleTemplate,
    PatternGenerator,
)
from soni.du.models import DialogueContext, MessageType, NLUOutput, SlotValue


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
    with pytest.raises(ValidationError):  # Pydantic raises ValidationError for frozen models
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
