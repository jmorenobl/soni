"""Unit tests for FlowManager.

All tests are async to match the async-first FlowManager design.
"""

import pytest

from soni.core.errors import FlowStackError
from soni.core.state import create_empty_dialogue_state
from soni.core.types import FlowContextState
from soni.flow.manager import FlowManager


class TestFlowManagerPushFlow:
    """Tests for pushing flows onto the stack."""

    @pytest.mark.asyncio
    async def test_push_flow_creates_context_on_empty_stack(self):
        """
        GIVEN an empty stack
        WHEN pushing a flow
        THEN stack has 1 item and slots are initialized
        """
        # Arrange
        state = create_empty_dialogue_state()
        manager = FlowManager()

        # Act
        flow_id = await manager.push_flow(state, "book_flight")

        # Assert
        assert len(state["flow_stack"]) == 1
        assert state["flow_stack"][0]["flow_name"] == "book_flight"
        assert state["flow_stack"][0]["flow_id"] == flow_id
        assert flow_id in state["flow_slots"]

    @pytest.mark.asyncio
    async def test_push_flow_with_inputs_stores_slots(self):
        """
        GIVEN inputs
        WHEN pushing a flow
        THEN inputs are stored in flow slots
        """
        # Arrange
        state = create_empty_dialogue_state()
        manager = FlowManager()

        # Act
        flow_id = await manager.push_flow(state, "book_flight", inputs={"origin": "NYC"})

        # Assert
        assert state["flow_slots"][flow_id]["origin"] == "NYC"
        assert manager.get_slot(state, "origin") == "NYC"


class TestFlowManagerPopFlow:
    """Tests for popping flows from the stack."""

    @pytest.mark.asyncio
    async def test_pop_flow_on_empty_stack_raises_error(self):
        """
        GIVEN empty stack
        WHEN pop_flow is called
        THEN raises FlowStackError
        """
        # Arrange
        state = create_empty_dialogue_state()
        manager = FlowManager()

        # Act & Assert
        with pytest.raises(FlowStackError):
            await manager.pop_flow(state)

    @pytest.mark.asyncio
    async def test_pop_flow_returns_context_and_updates_status(self):
        """
        GIVEN stack with 1 flow
        WHEN pop_flow is called
        THEN returns context with 'completed' status
        """
        # Arrange
        state = create_empty_dialogue_state()
        manager = FlowManager()
        await manager.push_flow(state, "flow1")

        # Act
        popped = await manager.pop_flow(state, result=FlowContextState.COMPLETED)

        # Assert
        assert len(state["flow_stack"]) == 0
        assert popped["flow_name"] == "flow1"
        assert popped["flow_state"] == "completed"


class TestFlowManagerSlots:
    """Tests for slot management."""

    @pytest.mark.asyncio
    async def test_set_and_get_slot(self):
        """
        GIVEN active flow
        WHEN set_slot is called
        THEN get_slot returns the value
        """
        # Arrange
        state = create_empty_dialogue_state()
        manager = FlowManager()
        await manager.push_flow(state, "flow1")

        # Act
        await manager.set_slot(state, "destination", "Paris")
        value = manager.get_slot(state, "destination")

        # Assert
        assert value == "Paris"

    @pytest.mark.asyncio
    async def test_get_slot_returns_none_if_not_found(self):
        # Arrange
        state = create_empty_dialogue_state()
        manager = FlowManager()
        await manager.push_flow(state, "flow1")

        # Act
        value = manager.get_slot(state, "non_existent")

        # Assert
        assert value is None

    @pytest.mark.asyncio
    async def test_get_all_slots(self):
        # Arrange
        state = create_empty_dialogue_state()
        manager = FlowManager()
        await manager.push_flow(state, "flow1")
        await manager.set_slot(state, "a", 1)
        await manager.set_slot(state, "b", 2)

        # Act
        slots = manager.get_all_slots(state)

        # Assert
        assert slots == {"a": 1, "b": 2}


class TestFlowManagerStep:
    """Tests for step advancement."""

    @pytest.mark.asyncio
    async def test_advance_step_increments_index(self):
        # Arrange
        state = create_empty_dialogue_state()
        manager = FlowManager()
        await manager.push_flow(state, "flow1")

        # Act
        success = await manager.advance_step(state)

        # Assert
        assert success is True
        assert state["flow_stack"][0]["step_index"] == 1

    @pytest.mark.asyncio
    async def test_advance_step_returns_false_on_empty_stack(self):
        # Arrange
        state = create_empty_dialogue_state()
        manager = FlowManager()

        # Act
        success = await manager.advance_step(state)

        # Assert
        assert success is False


class TestFlowManagerEdgeCases:
    """Tests for edge cases and optional methods."""

    @pytest.mark.asyncio
    async def test_handle_intent_change_pushes_new_flow(self):
        # Arrange
        state = create_empty_dialogue_state()
        manager = FlowManager()

        # Act
        await manager.handle_intent_change(state, "new_flow")

        # Assert
        assert len(state["flow_stack"]) == 1
        assert state["flow_stack"][0]["flow_name"] == "new_flow"

    @pytest.mark.asyncio
    async def test_handle_intent_change_skips_push_when_same_flow_active(self):
        """
        GIVEN a flow already active on the stack
        WHEN handle_intent_change is called with the same flow name
        THEN the flow is NOT pushed again (preserves existing slots)

        This prevents slot loss after digressions when user "restarts" same flow.
        """
        # Arrange
        state = create_empty_dialogue_state()
        manager = FlowManager()
        original_flow_id = await manager.push_flow(state, "transfer_funds")
        await manager.set_slot(state, "iban", "ES123456789")  # Existing slot

        # Act - Try to start same flow again (simulates NLU detecting StartFlow)
        await manager.handle_intent_change(state, "transfer_funds")

        # Assert - Should still have only 1 flow with preserved slots
        assert len(state["flow_stack"]) == 1
        assert state["flow_stack"][0]["flow_id"] == original_flow_id
        assert manager.get_slot(state, "iban") == "ES123456789"

    @pytest.mark.asyncio
    async def test_handle_intent_change_pushes_different_flow(self):
        """
        GIVEN a flow already active on the stack
        WHEN handle_intent_change is called with a DIFFERENT flow name
        THEN the new flow IS pushed (true intent switch)
        """
        # Arrange
        state = create_empty_dialogue_state()
        manager = FlowManager()
        await manager.push_flow(state, "transfer_funds")

        # Act - Switch to different flow
        await manager.handle_intent_change(state, "check_balance")

        # Assert - Should have 2 flows on stack
        assert len(state["flow_stack"]) == 2
        assert state["flow_stack"][0]["flow_name"] == "transfer_funds"
        assert state["flow_stack"][1]["flow_name"] == "check_balance"

    def test_get_active_context_returns_none_on_empty_stack(self):
        # Arrange
        state = create_empty_dialogue_state()
        manager = FlowManager()

        # Act
        context = manager.get_active_context(state)

        # Assert
        assert context is None

    @pytest.mark.asyncio
    async def test_set_slot_does_nothing_on_empty_stack(self):
        # Arrange
        state = create_empty_dialogue_state()
        manager = FlowManager()

        # Act
        await manager.set_slot(state, "key", "value")

        # Assert
        assert state["flow_slots"] == {}

    def test_get_all_slots_returns_empty_dict_on_empty_stack(self):
        # Arrange
        state = create_empty_dialogue_state()
        manager = FlowManager()

        # Act
        slots = manager.get_all_slots(state)

        # Assert
        assert slots == {}

    @pytest.mark.asyncio
    async def test_set_slot_initializes_slot_dict_if_missing(self):
        # Arrange
        state = create_empty_dialogue_state()
        manager = FlowManager()
        flow_id = await manager.push_flow(state, "flow1")
        # Manually corrupt state to remove slot dict
        del state["flow_slots"][flow_id]

        # Act
        await manager.set_slot(state, "key", "value")

        # Assert
        assert state["flow_slots"][flow_id]["key"] == "value"
