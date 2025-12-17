"""Tests for dataset.base module."""

import dspy
import pytest

from soni.core.commands import AffirmConfirmation, SetSlot, StartFlow
from soni.dataset.base import (
    ConversationContext,
    DomainConfig,
    DomainExampleData,
    ExampleTemplate,
    PatternGenerator,
)
from soni.dataset.constants import DEFAULT_EXAMPLE_DATETIME
from soni.du.models import NLUOutput


class TestDomainExampleData:
    """Tests for DomainExampleData class."""

    def test_default_initialization(self):
        """Test DomainExampleData can be created with defaults."""
        data = DomainExampleData()
        assert data.slot_values == {}
        assert data.trigger_intents == {}
        assert len(data.confirmation_positive) > 0
        assert len(data.confirmation_negative) > 0
        assert len(data.confirmation_unclear) > 0

    def test_custom_slot_values(self):
        """Test DomainExampleData with custom slot values."""
        data = DomainExampleData(
            slot_values={
                "origin": ["Madrid", "Barcelona"],
                "destination": ["Paris", "London"],
            }
        )
        assert data.slot_values["origin"] == ["Madrid", "Barcelona"]
        assert data.slot_values["destination"] == ["Paris", "London"]

    def test_get_slot_values_existing(self):
        """Test get_slot_values returns values for existing slot."""
        data = DomainExampleData(slot_values={"city": ["Madrid", "Barcelona"]})
        values = data.get_slot_values("city")
        assert values == ["Madrid", "Barcelona"]

    def test_get_slot_values_missing_returns_fallback(self):
        """Test get_slot_values returns fallback defaults for missing slot."""
        data = DomainExampleData()
        values = data.get_slot_values("nonexistent")
        # Fallback defaults are provided
        assert values == ["value1", "value2", "value3"]

    def test_get_trigger_intents_existing(self):
        """Test get_trigger_intents returns intents for existing flow."""
        data = DomainExampleData(trigger_intents={"book_flight": ["book a flight", "fly to"]})
        intents = data.get_trigger_intents("book_flight")
        assert intents == ["book a flight", "fly to"]

    def test_get_trigger_intents_missing(self):
        """Test get_trigger_intents returns empty list for missing flow."""
        data = DomainExampleData()
        intents = data.get_trigger_intents("nonexistent")
        assert intents == []


class TestDomainConfig:
    """Tests for DomainConfig class."""

    @pytest.fixture
    def sample_domain(self):
        """Create a sample domain configuration."""
        return DomainConfig(
            name="test_domain",
            description="Test domain for unit tests",
            available_flows=["flow_a", "flow_b"],
            flow_descriptions={"flow_a": "First flow", "flow_b": "Second flow"},
            available_actions=["action_1", "action_2"],
            slots={"slot1": "string", "slot2": "date"},
            slot_prompts={"slot1": "What is slot1?", "slot2": "What is slot2?"},
            example_data=DomainExampleData(
                slot_values={"slot1": ["value1", "value2"], "slot2": ["2024-01-01"]},
                trigger_intents={"flow_a": ["start flow a", "do flow a"]},
            ),
        )

    def test_domain_config_creation(self, sample_domain):
        """Test DomainConfig can be created."""
        assert sample_domain.name == "test_domain"
        assert len(sample_domain.available_flows) == 2
        assert len(sample_domain.slots) == 2

    def test_get_slot_values(self, sample_domain):
        """Test get_slot_values convenience method."""
        values = sample_domain.get_slot_values("slot1")
        assert values == ["value1", "value2"]

    def test_get_trigger_intents(self, sample_domain):
        """Test get_trigger_intents convenience method."""
        intents = sample_domain.get_trigger_intents("flow_a")
        assert intents == ["start flow a", "do flow a"]

    def test_get_primary_flow(self, sample_domain):
        """Test get_primary_flow returns first flow."""
        primary = sample_domain.get_primary_flow()
        assert primary == "flow_a"

    def test_create_example(self, sample_domain):
        """Test create_example factory method."""
        context = ConversationContext(
            history=dspy.History(messages=[]),
            current_slots={},
            current_flow="flow_a",
            expected_slots=["slot1"],
        )
        expected_output = NLUOutput(
            commands=[SetSlot(slot="slot1", value="test")],
            confidence=0.9,
        )

        example = sample_domain.create_example(
            user_message="test message",
            context=context,
            expected_output=expected_output,
            pattern="slot_value",
            context_type="ongoing",
        )

        assert example.user_message == "test message"
        assert example.domain == "test_domain"
        assert example.pattern == "slot_value"
        assert example.current_datetime == DEFAULT_EXAMPLE_DATETIME


class TestConversationContext:
    """Tests for ConversationContext class."""

    def test_default_creation(self):
        """Test ConversationContext with defaults."""
        context = ConversationContext(
            history=dspy.History(messages=[]),
            current_slots={},
            current_flow="test_flow",
            expected_slots=[],
        )
        assert context.current_flow == "test_flow"
        assert context.conversation_state is None

    def test_with_filled_slots(self):
        """Test ConversationContext with filled slots."""
        context = ConversationContext(
            history=dspy.History(messages=[{"user_message": "hi"}]),
            current_slots={"origin": "Madrid", "destination": "Paris"},
            current_flow="book_flight",
            expected_slots=["date"],
            conversation_state="collecting",
        )
        assert context.current_slots["origin"] == "Madrid"
        assert context.conversation_state == "collecting"


class TestExampleTemplate:
    """Tests for ExampleTemplate class."""

    @pytest.fixture
    def sample_domain(self):
        """Create a sample domain configuration."""
        return DomainConfig(
            name="test_domain",
            description="Test domain",
            available_flows=["test_flow"],
            flow_descriptions={"test_flow": "A test flow"},
            available_actions=["action1"],
            slots={"slot1": "string"},
            slot_prompts={"slot1": "What is slot1?"},
            example_data=DomainExampleData(
                slot_values={"slot1": ["val1"]},
                trigger_intents={"test_flow": ["start test"]},
            ),
        )

    def test_example_template_creation(self, sample_domain):
        """Test ExampleTemplate can be created."""
        template = ExampleTemplate(
            user_message="test",
            conversation_context=ConversationContext(
                history=dspy.History(messages=[]),
                current_slots={},
                current_flow="test_flow",
                expected_slots=["slot1"],
            ),
            expected_output=NLUOutput(
                commands=[SetSlot(slot="slot1", value="test")],
                confidence=0.9,
            ),
            domain="test_domain",
            pattern="slot_value",
            context_type="ongoing",
            current_datetime=DEFAULT_EXAMPLE_DATETIME,
        )
        assert template.user_message == "test"
        assert template.domain == "test_domain"

    def test_to_dspy_example(self, sample_domain):
        """Test to_dspy_example conversion."""
        template = ExampleTemplate(
            user_message="test message",
            conversation_context=ConversationContext(
                history=dspy.History(messages=[]),
                current_slots={"slot1": "value1"},
                current_flow="test_flow",
                expected_slots=["slot1"],
            ),
            expected_output=NLUOutput(
                commands=[SetSlot(slot="slot1", value="value1")],
                confidence=0.9,
            ),
            domain="test_domain",
            pattern="slot_value",
            context_type="ongoing",
            current_datetime=DEFAULT_EXAMPLE_DATETIME,
        )

        dspy_example = template.to_dspy_example(sample_domain)

        # Verify the dspy.Example structure
        assert dspy_example.user_message == "test message"
        assert dspy_example.context.active_flow == "test_flow"
        assert dspy_example.context.expected_slot == "slot1"
        assert len(dspy_example.context.available_flows) == 1
        assert len(dspy_example.context.available_commands) == 8
        assert len(dspy_example.context.current_slots) == 1

    def test_to_dspy_example_idle_state(self, sample_domain):
        """Test to_dspy_example with idle conversation state."""
        template = ExampleTemplate(
            user_message="start",
            conversation_context=ConversationContext(
                history=dspy.History(messages=[]),
                current_slots={},
                current_flow="none",
                expected_slots=[],
                conversation_state=None,
            ),
            expected_output=NLUOutput(
                commands=[StartFlow(flow_name="test_flow")],
                confidence=0.9,
            ),
            domain="test_domain",
            pattern="interruption",
            context_type="cold_start",
            current_datetime=DEFAULT_EXAMPLE_DATETIME,
        )

        dspy_example = template.to_dspy_example(sample_domain)
        assert dspy_example.context.active_flow is None
        assert dspy_example.context.conversation_state == "idle"


class TestPatternGenerator:
    """Tests for PatternGenerator base class."""

    def test_generate_examples_not_implemented(self):
        """Test that base generate_examples raises NotImplementedError."""
        gen = PatternGenerator()
        with pytest.raises(NotImplementedError):
            gen.generate_examples(None, "ongoing", 3)
