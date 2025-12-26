"""Tests for base dataset models and classes."""

import dspy
import pytest

from soni.dataset.base import ConversationContext, DomainConfig, DomainExampleData, ExampleTemplate
from soni.du.models import NLUOutput


class TestExampleTemplate:
    """Tests for ExampleTemplate class."""

    def test_example_creation(self):
        """ExampleTemplate should be created correctly."""
        example = ExampleTemplate(
            user_message="Hello",
            conversation_context=ConversationContext(
                current_flow="test_flow",
                history=dspy.History(messages=[]),
                current_slots={},
                expected_slots=[],
            ),
            expected_output=NLUOutput(commands=[]),
            domain="test",
            pattern="test_pattern",
            context_type="ongoing",
        )
        assert example.user_message == "Hello"
        assert example.conversation_context.current_flow == "test_flow"


class TestConversationContext:
    """Tests for ConversationContext class."""

    def test_conversation_context_validation(self):
        """ConversationContext requires history, current_slots, etc."""
        ctx = ConversationContext(
            current_flow="test_flow",
            history=dspy.History(messages=[]),
            current_slots={"slot1": "val1"},
            expected_slots=["slot2"],
        )
        assert ctx.current_flow == "test_flow"
        assert ctx.current_slots["slot1"] == "val1"


class TestDomainConfig:
    """Tests for DomainConfig class."""

    def test_domain_config_init(self):
        """Should initialize with slots and flows."""
        config = DomainConfig(
            name="test",
            description="test desc",
            available_flows=["f1"],
            available_actions=["a1"],
            flow_descriptions={"f1": "desc"},
            slots={"s1": "string"},
            slot_prompts={"s1": "prompt"},
            example_data=DomainExampleData(
                slot_values={},
                trigger_intents={},
                confirmation_positive=[],
                confirmation_negative=[],
                confirmation_unclear=[],
            ),
        )
        assert config.name == "test"
        assert config.get_primary_flow() == "f1"

    def test_get_slot_values(self):
        """Should return sample values if provided in config."""
        config = DomainConfig(
            name="test",
            description="test desc",
            available_flows=[],
            available_actions=[],
            flow_descriptions={},
            slots={"destination": "string"},
            slot_prompts={"destination": "prompt"},
            example_data=DomainExampleData(
                slot_values={"destination": ["Madrid", "London"]},
                trigger_intents={},
                confirmation_positive=[],
                confirmation_negative=[],
                confirmation_unclear=[],
            ),
        )
        assert config.get_slot_values("destination") == ["Madrid", "London"]
        # Should return default values (value1, value2, value3) if not found in slot_values
        assert config.get_slot_values("unknown") == ["value1", "value2", "value3"]
