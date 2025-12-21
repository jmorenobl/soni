"""Unit tests for Node Factories."""

from unittest.mock import AsyncMock, Mock

import pytest
from soni.compiler.nodes.branch import BranchNodeFactory

from soni.compiler.nodes import (
    ActionNodeFactory,
    CollectNodeFactory,
    ConfirmNodeFactory,
    SayNodeFactory,
    WhileNodeFactory,
)
from soni.config import (
    ActionStepConfig,
    BranchStepConfig,
    CollectStepConfig,
    ConfirmStepConfig,
    SayStepConfig,
    WhileStepConfig,
)
from soni.core.state import create_empty_dialogue_state


# Mocking helper
def create_mock_config(fm=None, ah=None):
    from langgraph.runtime import Runtime

    from soni.config import SoniConfig

    context = Mock()
    context.flow_manager = fm or Mock()
    context.action_handler = ah or Mock()
    # Use real config
    context.config = SoniConfig(flows={}, slots={})

    # Return Runtime object
    return Runtime(
        context=context,
        store=None,
        stream_writer=lambda x: None,
        previous=None,
    )


class TestCollectNodeFactory:
    """Tests for CollectNodeFactory."""

    @pytest.mark.asyncio
    async def test_collect_node_prompts_when_slot_empty(self):
        """
        GIVEN a collect step for an empty slot with SetSlot command
        WHEN node is executed
        THEN uses command value without interrupting
        """
        # Arrange
        step = CollectStepConfig(step="get_origin", type="collect", slot="origin")
        factory = CollectNodeFactory()

        # Mock dependencies
        mock_fm = Mock()
        mock_fm.get_slot.return_value = None  # Slot is empty
        mock_fm.set_slot.return_value = None  # No delta

        runtime = create_mock_config(fm=mock_fm)

        state = create_empty_dialogue_state()
        # Add SetSlot command (NLU provided value)
        state["commands"] = [{"type": "SetSlot", "slot": "origin", "value": "Madrid"}]

        # Act
        node = factory.create(step)
        result = await node(state, runtime)

        # Assert - should use command value
        mock_fm.set_slot.assert_called_once_with(state, "origin", "Madrid")
        assert result["waiting_for_slot"] is None

    @pytest.mark.asyncio
    async def test_collect_node_continues_when_slot_filled(self):
        """
        GIVEN a collect step for a filled slot
        WHEN node is executed
        THEN returns 'active' state
        """
        # Arrange
        step = CollectStepConfig(step="get_origin", type="collect", slot="origin")
        factory = CollectNodeFactory()

        # Mock dependencies
        mock_fm = Mock()
        mock_fm.get_slot.return_value = "NYC"  # Slot is filled

        runtime = create_mock_config(fm=mock_fm)

        state = create_empty_dialogue_state()

        # Act
        node = factory.create(step)
        result = await node(state, runtime)

        # Assert - slot filled, returns dict with cleared branch target
        assert isinstance(result, dict)
        assert result == {"_branch_target": None}


class TestActionNodeFactory:
    """Tests for ActionNodeFactory."""

    @pytest.mark.asyncio
    async def test_action_node_executes_action(self):
        """
        GIVEN an action step
        WHEN node is executed
        THEN executes action via handler
        """
        # Arrange
        step = ActionStepConfig(step="do_booking", type="action", call="book_flight_api")
        factory = ActionNodeFactory()

        mock_handler = AsyncMock()
        runtime = create_mock_config(ah=mock_handler)

        state = create_empty_dialogue_state()

        # Act
        node = factory.create(step)
        await node(state, runtime)

        # Assert
        mock_handler.execute.assert_called_once()
        args = mock_handler.execute.call_args
        assert args[0][0] == "book_flight_api"


class TestSayNodeFactory:
    """Tests for SayNodeFactory."""

    @pytest.mark.asyncio
    async def test_say_node_returns_response(self):
        """
        GIVEN a say step
        WHEN node is executed
        THEN returns response
        """
        # Arrange
        step = SayStepConfig(step="greet", type="say", message="Hello")
        factory = SayNodeFactory()

        mock_fm = Mock()
        mock_fm.get_all_slots.return_value = {}
        runtime = create_mock_config(fm=mock_fm)
        state = create_empty_dialogue_state()

        # Act
        node = factory.create(step)
        result = await node(state, runtime)

        # Assert
        assert isinstance(result, dict)
        assert result["last_response"] == "Hello"


class TestBranchNodeFactory:
    """Tests for BranchNodeFactory."""

    @pytest.mark.asyncio
    async def test_branch_node_routes_based_on_slot(self):
        """
        GIVEN a branch step with cases
        WHEN node is executed (and slot matches case)
        THEN returns _branch_target in state for router
        """

        # Arrange
        step = BranchStepConfig(
            step="check_user_type",
            type="branch",
            slot="user_type",
            cases={"gold": "vip_flow", "regular": "standard_flow"},
        )
        factory = BranchNodeFactory()

        # Mock FM to return 'gold'
        mock_fm = Mock()
        mock_fm.get_slot.return_value = "gold"

        runtime = create_mock_config(fm=mock_fm)

        state = create_empty_dialogue_state()

        # Act
        node = factory.create(step)
        result = await node(state, runtime)

        # Assert - branch now uses state-based routing, not Command
        assert result == {"_branch_target": "vip_flow"}

    @pytest.mark.asyncio
    async def test_branch_node_uses_default_if_no_match(self):
        """
        GIVEN a branch step
        WHEN slot does not match any case
        THEN returns _branch_target = None to proceed to next step
        """

        # Arrange
        step = BranchStepConfig(
            step="check_user_type",
            type="branch",
            slot="user_type",
            cases={"gold": "vip_flow"},
        )
        factory = BranchNodeFactory()

        # Mock FM to return 'silver' (not in cases)
        mock_fm = Mock()
        mock_fm.get_slot.return_value = "silver"

        runtime = create_mock_config(fm=mock_fm)

        state = create_empty_dialogue_state()

        # Act
        node = factory.create(step)
        result = await node(state, runtime)

        # Assert - no match returns empty dict, router will route to default next step
        assert result == {}


class TestConfirmNodeFactory:
    """Tests for ConfirmNodeFactory."""

    @pytest.mark.asyncio
    async def test_confirm_node_collects_slot_if_missing(self):
        """
        GIVEN a confirm step with empty slot AND affirm command
        WHEN node is executed
        THEN sets slot to True
        """
        # Arrange
        step = ConfirmStepConfig(step="confirm_booking", type="confirm", slot="booking_confirmed")
        factory = ConfirmNodeFactory()

        # Mock dependencies
        mock_fm = Mock()
        mock_fm.get_slot.return_value = None  # Slot is empty
        mock_fm.set_slot.return_value = None

        runtime = create_mock_config(fm=mock_fm)

        # State WITH affirm command (command-based approach)
        state = create_empty_dialogue_state()
        state["commands"] = [{"type": "affirm_confirmation"}]

        # Act
        node = factory.create(step)
        result = await node(state, runtime)

        # Assert - should set slot to True and proceed
        mock_fm.set_slot.assert_called_with(state, "booking_confirmed", True)
        assert result.get("flow_state") == "active"

    @pytest.mark.asyncio
    async def test_confirm_node_validates_value(self):
        """
        GIVEN a confirm step with filled slot
        WHEN node is executed
        THEN returns empty dict (idempotent, no state change)
        """
        # Arrange
        step = ConfirmStepConfig(step="confirm_booking", type="confirm", slot="booking_confirmed")
        factory = ConfirmNodeFactory()

        # Mock dependencies
        mock_fm = Mock()
        mock_fm.get_slot.return_value = True  # Slot already confirmed

        runtime = create_mock_config(fm=mock_fm)

        state = create_empty_dialogue_state()

        # Act
        node = factory.create(step)
        result = await node(state, runtime)

        # Assert - no state change when slot already filled (except clearing branch target)
        assert result == {"_branch_target": None}


class TestWhileNodeFactory:
    """Tests for WhileNodeFactory."""

    @pytest.mark.asyncio
    async def test_while_node_loops_if_condition_true(self):
        """
        GIVEN a while step
        WHEN condition is true
        THEN branches to loop start/body
        """
        from langgraph.types import Command

        # 'do' contains list of steps to execute in loop.
        # In this simplistic test, we check if it validates condition.
        # But 'while' node logic is tricky: it acts as the loop guard.
        # If true -> goto body_start; else -> goto next_step (implicit).

        step = WhileStepConfig(
            step="loop_chk", type="while", condition="slot_x == 'value'", do=["step1"]
        )
        factory = WhileNodeFactory()

        # Mock logic - now uses get_all_slots
        mock_fm = Mock()
        mock_fm.get_all_slots.return_value = {"slot_x": "value"}

        runtime = create_mock_config(fm=mock_fm)

        node = factory.create(step)
        result = await node(create_empty_dialogue_state(), runtime)

        assert isinstance(result, Command)
        assert result.goto == "step1"

    @pytest.mark.asyncio
    async def test_while_node_exits_loop_if_condition_false(self):
        step = WhileStepConfig(
            step="loop_chk", type="while", condition="slot_x == 'value'", do=["step1"]
        )
        factory = WhileNodeFactory()

        mock_fm = Mock()
        mock_fm.get_all_slots.return_value = {"slot_x": "other"}
        runtime = create_mock_config(fm=mock_fm)

        node = factory.create(step)
        result = await node(create_empty_dialogue_state(), runtime)

        assert result == {}
