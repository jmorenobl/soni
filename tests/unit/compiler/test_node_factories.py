"""Unit tests for Node Factories."""

from dataclasses import dataclass
from typing import Any
from unittest.mock import AsyncMock, Mock

import pytest

from soni.compiler.nodes.base import NodeFunction
from soni.compiler.nodes.collect import CollectNodeFactory
from soni.core.config import StepConfig
from soni.core.state import create_empty_dialogue_state
from soni.core.types import DialogueState, RuntimeContext


# Mocking helper
def create_mock_config(fm=None, ah=None):
    context = Mock()
    context.flow_manager = fm or Mock()
    context.action_handler = ah or Mock()
    return {"configurable": {"runtime_context": context}}


class TestCollectNodeFactory:
    """Tests for CollectNodeFactory."""

    @pytest.mark.asyncio
    async def test_collect_node_prompts_when_slot_empty(self):
        """
        GIVEN a collect step for an empty slot
        WHEN node is executed
        THEN returns 'waiting_input' and prompt
        """
        # Arrange
        step = StepConfig(step="get_origin", type="collect", slot="origin")
        factory = CollectNodeFactory()

        # Mock dependencies
        mock_fm = Mock()
        mock_fm.get_slot.return_value = None  # Slot is empty

        runtime = create_mock_config(fm=mock_fm)

        state = create_empty_dialogue_state()

        # Act
        node = factory.create(step)
        result = await node(state, runtime)

        # Assert
        assert result["flow_state"] == "waiting_input"

        assert result["waiting_for_slot"] == "origin"
        assert "last_response" in result

    @pytest.mark.asyncio
    async def test_collect_node_continues_when_slot_filled(self):
        """
        GIVEN a collect step for a filled slot
        WHEN node is executed
        THEN returns 'active' state
        """
        # Arrange
        step = StepConfig(step="get_origin", type="collect", slot="origin")
        factory = CollectNodeFactory()

        # Mock dependencies
        mock_fm = Mock()
        mock_fm.get_slot.return_value = "NYC"  # Slot is filled

        runtime = create_mock_config(fm=mock_fm)

        state = create_empty_dialogue_state()

        # Act
        node = factory.create(step)
        result = await node(state, runtime)

        # Assert
        assert result["flow_state"] == "active"


class TestActionNodeFactory:
    """Tests for ActionNodeFactory."""

    @pytest.mark.asyncio
    async def test_action_node_executes_action(self):
        """
        GIVEN an action step
        WHEN node is executed
        THEN executes action via handler
        """
        from soni.compiler.nodes.action import ActionNodeFactory

        # Arrange
        step = StepConfig(step="do_booking", type="action", call="book_flight_api")
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
        from soni.compiler.nodes.say import SayNodeFactory

        # Arrange
        step = StepConfig(step="greet", type="say", message="Hello")
        factory = SayNodeFactory()

        mock_fm = Mock()
        mock_fm.get_all_slots.return_value = {}
        runtime = create_mock_config(fm=mock_fm)
        state = create_empty_dialogue_state()

        # Act
        node = factory.create(step)
        result = await node(state, runtime)

        # Assert
        assert result["last_response"] == "Hello"


class TestBranchNodeFactory:
    """Tests for BranchNodeFactory."""

    @pytest.mark.asyncio
    async def test_branch_node_routes_based_on_slot(self):
        """
        GIVEN a branch step with cases
        WHEN node is executed (and slot matches case)
        THEN returns Command to jump
        """
        from langgraph.types import Command

        from soni.compiler.nodes.branch import BranchNodeFactory

        # Arrange
        step = StepConfig(
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

        # Assert
        assert isinstance(result, Command)
        assert result.goto == "vip_flow"

    @pytest.mark.asyncio
    async def test_branch_node_uses_default_if_no_match(self):
        """
        GIVEN a branch step
        WHEN slot does not match any case
        THEN proceeds (returns empty dict or default jump if implemented)
        """
        from soni.compiler.nodes.branch import BranchNodeFactory

        # Arrange
        step = StepConfig(
            step="check_user_type", type="branch", slot="user_type", cases={"gold": "vip_flow"}
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

        # Assert
        # Should just return empty dict to proceed to next step in sequence
        assert result == {}


class TestConfirmNodeFactory:
    """Tests for ConfirmNodeFactory."""

    @pytest.mark.asyncio
    async def test_confirm_node_collects_slot_if_missing(self):
        """
        GIVEN a confirm step
        WHEN slot is empty
        THEN prompts user
        """
        from soni.compiler.nodes.confirm import ConfirmNodeFactory

        # Arrange
        step = StepConfig(step="confirm_booking", type="confirm", slot="confirmed")
        factory = ConfirmNodeFactory()

        mock_fm = Mock()
        mock_fm.get_slot.return_value = None
        mock_fm.get_all_slots.return_value = {}  # Required for prompt formatting

        runtime = create_mock_config(fm=mock_fm)

        # Act
        node = factory.create(step)
        result = await node(create_empty_dialogue_state(), runtime)

        # Assert
        assert result["flow_state"] == "waiting_input"
        assert result["waiting_for_slot"] == "confirmed"

    @pytest.mark.asyncio
    async def test_confirm_node_validates_value(self):
        """
        GIVEN a confirm step
        WHEN slot has value
        THEN returns active (logic to act on confirmation is separate or defaults)
        """
        from soni.compiler.nodes.confirm import ConfirmNodeFactory

        step = StepConfig(step="confirm_booking", type="confirm", slot="confirmed")
        factory = ConfirmNodeFactory()

        mock_fm = Mock()
        mock_fm.get_slot.return_value = True

        runtime = create_mock_config(fm=mock_fm)

        node = factory.create(step)
        result = await node(create_empty_dialogue_state(), runtime)

        assert result["flow_state"] == "active"


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

        from soni.compiler.nodes.while_loop import WhileNodeFactory

        # 'do' contains list of steps to execute in loop.
        # In this simplistic test, we check if it validates condition.
        # But 'while' node logic is tricky: it acts as the loop guard.
        # If true -> goto body_start; else -> goto next_step (implicit).

        step = StepConfig(
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
        from soni.compiler.nodes.while_loop import WhileNodeFactory

        step = StepConfig(
            step="loop_chk", type="while", condition="slot_x == 'value'", do=["step1"]
        )
        factory = WhileNodeFactory()

        mock_fm = Mock()
        mock_fm.get_all_slots.return_value = {"slot_x": "other"}
        runtime = create_mock_config(fm=mock_fm)

        node = factory.create(step)
        result = await node(create_empty_dialogue_state(), runtime)

        assert result == {}
