"""Tests for DM nodes."""

from dataclasses import dataclass
from unittest.mock import Mock

import pytest
from langgraph.types import Command

from soni.core.constants import NodeName
from soni.core.state import create_empty_dialogue_state
from soni.core.types import DialogueState, FlowContext, FlowContextState, RuntimeContext


@dataclass
class MockContext:
    flow_manager: Mock


class TestExecuteNode:
    """Tests for execute_node routing."""

    @pytest.mark.asyncio
    async def test_execute_routes_to_active_flow(self):
        """
        GIVEN stack has active flow
        WHEN execute_node runs
        THEN returns Command(goto="flow_{name}")
        """
        from soni.dm.nodes.execute import execute_node

        # Arrange
        state = create_empty_dialogue_state()
        flow_ctx: FlowContext = {
            "flow_id": "123",
            "flow_name": "book_flight",
            "flow_state": FlowContextState.ACTIVE,
            "current_step": None,
            "step_index": 0,
            "outputs": {},
            "started_at": 0.0,
        }
        state["flow_stack"] = [flow_ctx]

        mock_fm = Mock()
        mock_fm.get_active_context.return_value = flow_ctx

        from langchain_core.runnables import RunnableConfig

        context = Mock()
        context.flow_manager = mock_fm
        config = RunnableConfig(configurable={"runtime_context": context})

        # Ac
        result = await execute_node(state, config)

        # Asser
        assert isinstance(result, Command)
        assert result.goto == "flow_book_flight"

    @pytest.mark.asyncio
    async def test_execute_routes_to_respond_if_no_flow(self):
        """
        GIVEN stack is empty
        WHEN execute_node runs
        THEN routes to respond (or handles error)
        """
        from soni.dm.nodes.execute import execute_node

        state = create_empty_dialogue_state()
        mock_fm = Mock()
        mock_fm.get_active_context.return_value = None

        from langchain_core.runnables import RunnableConfig

        context = Mock()
        context.flow_manager = mock_fm
        config = RunnableConfig(configurable={"runtime_context": context})

        result = await execute_node(state, config)

        # If no flow, usually we just respond (maybe with fallback)
        # Assuming simple sequential edge or explicit command.
        # Actually execute_node is the router. If nothing to execute, go to respond.
        assert isinstance(result, Command)
        assert result.goto == NodeName.RESPOND
