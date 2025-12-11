"""Unit tests for dataset registry utilities."""

import dspy
import pytest

from soni.dataset.base import ConversationContext, DomainConfig, ExampleTemplate
from soni.dataset.registry import print_dataset_stats, validate_dataset
from soni.du.models import MessageType, NLUOutput, SlotValue


def test_validate_dataset_empty():
    """Test validate_dataset raises error for empty dataset."""
    # Act & Assert
    with pytest.raises(ValueError, match="Dataset is empty"):
        validate_dataset([])


def test_validate_dataset_valid():
    """Test validate_dataset returns stats for valid dataset."""
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

    example = template.to_dspy_example(domain_config)

    # Act
    stats = validate_dataset([example])

    # Assert
    assert stats["total_examples"] == 1
    assert MessageType.SLOT_VALUE in stats["patterns"]
    assert stats["patterns"][MessageType.SLOT_VALUE] == 1
    assert len(stats["validation_errors"]) == 0


def test_validate_dataset_missing_field():
    """Test validate_dataset detects missing fields."""

    # Arrange
    # Create an example-like object missing a required field
    class IncompleteExample:
        user_message = "test"
        history = dspy.History(messages=[])
        context = None
        # Missing 'result' field

    incomplete_example = IncompleteExample()

    # Act & Assert
    with pytest.raises(ValueError, match="Dataset validation failed"):
        validate_dataset([incomplete_example])


def test_validate_dataset_imbalanced_distribution():
    """Test validate_dataset detects imbalanced pattern distribution."""
    # Arrange
    domain_config = DomainConfig(
        name="test_domain",
        description="Test",
        available_flows=["book_flight"],
        available_actions=["search_flights"],
        slots={"origin": "city"},
        slot_prompts={"origin": "Which city?"},
    )

    # Create many examples of one pattern and few of another
    templates_slot_value = [
        ExampleTemplate(
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
                reasoning="Test",
            ),
            domain="test_domain",
            pattern="slot_value",
            context_type="ongoing",
        )
        for _ in range(10)
    ]

    templates_correction = [
        ExampleTemplate(
            user_message="No, Barcelona",
            conversation_context=ConversationContext(
                history=dspy.History(messages=[]),
                current_slots={"origin": "Madrid"},
                current_flow="book_flight",
                expected_slots=[],
            ),
            expected_output=NLUOutput(
                message_type=MessageType.CORRECTION,
                command="book_flight",
                slots=[SlotValue(name="origin", value="Barcelona", confidence=0.9)],
                confidence=0.9,
                reasoning="Test",
            ),
            domain="test_domain",
            pattern="correction",
            context_type="ongoing",
        )
        for _ in range(1)  # Only 1 correction vs 10 slot_value
    ]

    examples = [
        template.to_dspy_example(domain_config)
        for template in templates_slot_value + templates_correction
    ]

    # Act & Assert - should detect imbalance (10 > 3 * 1)
    with pytest.raises(ValueError, match="Imbalanced pattern distribution"):
        validate_dataset(examples)


def test_print_dataset_stats(capsys):
    """Test print_dataset_stats prints statistics."""
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

    example = template.to_dspy_example(domain_config)

    # Act
    print_dataset_stats([example])

    # Assert
    captured = capsys.readouterr()
    assert "Dataset Statistics" in captured.out
    assert "Total examples: 1" in captured.out
    assert "Pattern distribution" in captured.out
