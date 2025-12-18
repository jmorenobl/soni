"""Tests for SetNodeFactory."""

import pytest
from langchain_core.runnables import RunnableConfig
from pydantic import ValidationError

from soni.compiler.nodes.set import SetNodeFactory
from soni.core.config import SetStepConfig
from soni.core.constants import FlowContextState, FlowState
from soni.core.errors import ValidationError as SoniValidationError
from soni.core.types import DialogueState, RuntimeContext
from soni.flow.manager import FlowManager


@pytest.fixture
def flow_manager():
    """Create a FlowManager instance."""
    return FlowManager()


@pytest.fixture
def runtime_context(flow_manager):
    """Create a RuntimeContext for testing."""
    from soni.core.config import SoniConfig

    config = SoniConfig(flows={})
    return RuntimeContext(
        config=config,
        flow_manager=flow_manager,
        action_handler=None,  # type: ignore
        du=None,  # type: ignore
    )


@pytest.fixture
def config_with_context(runtime_context):
    """Create a RunnableConfig with RuntimeContext."""
    return RunnableConfig(configurable={"runtime_context": runtime_context})


@pytest.fixture
def dialogue_state_with_flow(flow_manager):
    """Create a DialogueState with an active flow."""
    import time

    state: DialogueState = {
        "user_message": None,
        "last_response": "",
        "messages": [],
        "flow_stack": [
            {
                "flow_name": "test_flow",
                "flow_id": "test_flow_123",
                "flow_state": FlowContextState.ACTIVE,
                "current_step": None,
                "step_index": 0,
                "outputs": {},
                "started_at": time.time(),
            }
        ],
        "flow_slots": {"test_flow_123": {}},
        "flow_state": FlowState.ACTIVE,
        "waiting_for_slot": None,
        "waiting_for_slot_type": None,
        "commands": [],
        "response": None,
        "action_result": None,
        "_branch_target": None,
        "turn_count": 1,
        "metadata": {},
    }
    return state


class TestSetNodeFactory:
    """Tests for SetNodeFactory."""

    def test_missing_slots_raises_error(self):
        """Test that missing slots field raises ValidationError."""
        # Pydantic v2 validation happens at instantiation
        with pytest.raises(ValidationError) as exc_info:
            SetStepConfig(step="bad_set", type="set")

        assert "slots" in str(exc_info.value)

    def test_invalid_slots_type_raises_error(self):
        """Test that non-dict slots raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            SetStepConfig(
                step="bad_set",
                type="set",
                slots=["slot1", "slot2"],
            )

        # Pydantic validation message
        assert "Input should be a valid dictionary" in str(exc_info.value) or "slots" in str(
            exc_info.value
        )

    @pytest.mark.asyncio
    async def test_set_literal_values(
        self,
        dialogue_state_with_flow,
        config_with_context,
        flow_manager,
    ):
        """Test setting literal values (string, int, bool, float)."""
        factory = SetNodeFactory()
        step = SetStepConfig(
            step="set_literals",
            type="set",
            slots={
                "name": "Alice",
                "age": 30,
                "is_active": True,
                "balance": 1234.56,
            },
        )

        node = factory.create(step)
        await node(dialogue_state_with_flow, config_with_context)

        # Check slots were set
        flow_id = "test_flow_123"
        slots = dialogue_state_with_flow["flow_slots"][flow_id]

        assert slots["name"] == "Alice"
        assert slots["age"] == 30
        assert slots["is_active"] is True
        assert slots["balance"] == 1234.56

    @pytest.mark.asyncio
    async def test_set_with_template_substitution(
        self,
        dialogue_state_with_flow,
        config_with_context,
        flow_manager,
    ):
        """Test setting values with template substitution."""
        # Pre-populate some slots
        flow_id = "test_flow_123"
        dialogue_state_with_flow["flow_slots"][flow_id] = {
            "first_name": "Bob",
            "account_type": "premium",
        }

        factory = SetNodeFactory()
        step = SetStepConfig(
            step="set_templates",
            type="set",
            slots={
                "greeting": "Hello, {{first_name}}!",
                "user_type": "{{account_type}}",
                "combo": "{{first_name}} has {{account_type}}",
            },
        )

        node = factory.create(step)
        await node(dialogue_state_with_flow, config_with_context)

        slots = dialogue_state_with_flow["flow_slots"][flow_id]

        assert slots["greeting"] == "Hello, Bob!"
        assert slots["user_type"] == "premium"
        assert slots["combo"] == "Bob has premium"

    @pytest.mark.asyncio
    async def test_set_with_missing_template_slot(
        self,
        dialogue_state_with_flow,
        config_with_context,
        flow_manager,
        caplog,
    ):
        """Test that missing template slot logs warning and uses literal."""
        factory = SetNodeFactory()
        step = SetStepConfig(
            step="set_missing_template",
            type="set",
            slots={
                "message": "Hello, {{missing_slot}}!",
            },
        )

        node = factory.create(step)
        await node(dialogue_state_with_flow, config_with_context)

        flow_id = "test_flow_123"
        slots = dialogue_state_with_flow["flow_slots"][flow_id]

        # Should fallback to literal value
        assert slots["message"] == "Hello, {{missing_slot}}!"
        # Should log warning
        assert "Template substitution failed" in caplog.text

    @pytest.mark.asyncio
    async def test_conditional_execution_true(
        self,
        dialogue_state_with_flow,
        config_with_context,
        flow_manager,
    ):
        """Test that condition=true executes the set."""
        # Pre-populate condition slot
        flow_id = "test_flow_123"
        dialogue_state_with_flow["flow_slots"][flow_id] = {
            "is_premium": True,
        }

        factory = SetNodeFactory()
        step = SetStepConfig(
            step="set_conditional",
            type="set",
            condition="is_premium",
            slots={
                "max_transfers": 100,
            },
        )

        node = factory.create(step)
        await node(dialogue_state_with_flow, config_with_context)

        slots = dialogue_state_with_flow["flow_slots"][flow_id]

        # Condition true - should set
        assert slots["max_transfers"] == 100

    @pytest.mark.asyncio
    async def test_conditional_execution_false(
        self,
        dialogue_state_with_flow,
        config_with_context,
        flow_manager,
    ):
        """Test that condition=false skips the set."""
        # Pre-populate condition slot
        flow_id = "test_flow_123"
        dialogue_state_with_flow["flow_slots"][flow_id] = {
            "is_premium": False,
        }

        factory = SetNodeFactory()
        step = SetStepConfig(
            step="set_conditional",
            type="set",
            condition="is_premium",
            slots={
                "max_transfers": 100,
            },
        )

        node = factory.create(step)
        await node(dialogue_state_with_flow, config_with_context)

        slots = dialogue_state_with_flow["flow_slots"][flow_id]

        # Condition false - should NOT set
        assert "max_transfers" not in slots

    @pytest.mark.asyncio
    async def test_multiple_slots_in_one_step(
        self,
        dialogue_state_with_flow,
        config_with_context,
        flow_manager,
    ):
        """Test setting multiple slots in a single step."""
        factory = SetNodeFactory()
        step = SetStepConfig(
            step="set_many",
            type="set",
            slots={
                "slot1": "value1",
                "slot2": 42,
                "slot3": True,
                "slot4": 3.14,
                "slot5": "another value",
            },
        )

        node = factory.create(step)
        await node(dialogue_state_with_flow, config_with_context)

        flow_id = "test_flow_123"
        slots = dialogue_state_with_flow["flow_slots"][flow_id]

        assert len(slots) == 5
        assert slots["slot1"] == "value1"
        assert slots["slot2"] == 42
        assert slots["slot3"] is True
        assert slots["slot4"] == 3.14
        assert slots["slot5"] == "another value"

    @pytest.mark.asyncio
    async def test_empty_slots_dict(
        self,
        dialogue_state_with_flow,
        config_with_context,
        flow_manager,
    ):
        """Test that empty slots dict raises ValidationError."""
        factory = SetNodeFactory()
        step = SetStepConfig(
            step="set_empty",
            type="set",
            slots={},
        )

        with pytest.raises(SoniValidationError, match="cannot be empty"):
            factory.create(step)

    @pytest.mark.asyncio
    async def test_overwrite_existing_slot(
        self,
        dialogue_state_with_flow,
        config_with_context,
        flow_manager,
    ):
        """Test that set can overwrite existing slot values."""
        # Pre-populate
        flow_id = "test_flow_123"
        dialogue_state_with_flow["flow_slots"][flow_id] = {
            "counter": 0,
        }

        factory = SetNodeFactory()
        step = SetStepConfig(
            step="increment",
            type="set",
            slots={
                "counter": 1,
            },
        )

        node = factory.create(step)
        await node(dialogue_state_with_flow, config_with_context)

        slots = dialogue_state_with_flow["flow_slots"][flow_id]

        # Should overwrite
        assert slots["counter"] == 1

    @pytest.mark.asyncio
    async def test_set_with_complex_condition(
        self,
        dialogue_state_with_flow,
        config_with_context,
        flow_manager,
    ):
        """Test set with complex condition expression."""
        # Pre-populate
        flow_id = "test_flow_123"
        dialogue_state_with_flow["flow_slots"][flow_id] = {
            "account_type": "premium",
            "age": 25,
        }

        factory = SetNodeFactory()
        step = SetStepConfig(
            step="set_complex",
            type="set",
            condition="account_type == 'premium' AND age > 18",
            slots={
                "eligible": True,
            },
        )

        node = factory.create(step)
        await node(dialogue_state_with_flow, config_with_context)

        slots = dialogue_state_with_flow["flow_slots"][flow_id]

        # Complex condition true - should set
        assert slots["eligible"] is True
