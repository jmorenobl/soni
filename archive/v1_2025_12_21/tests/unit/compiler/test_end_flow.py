"""Unit tests for SubgraphBuilder and end_flow_node."""

from unittest.mock import MagicMock

import pytest
from langchain_core.runnables import RunnableConfig
from soni.compiler.subgraph import END_FLOW_NODE, SubgraphBuilder, end_flow_node
from soni.core.constants import FlowContextState
from soni.core.state import create_empty_dialogue_state

from soni.config import FlowConfig, SayStepConfig


class TestEndFlowNode:
    """Tests for end_flow_node function.

    Note: Stack management (pop) is handled by resume_node in the orchestrator.
    end_flow_node just marks the subgraph as complete and returns.
    """

    @pytest.mark.asyncio
    async def test_returns_empty_dict(self):
        """
        GIVEN a flow completing its execution
        WHEN end_flow_node is called
        THEN returns empty dict (stack pop handled by resume_node)
        """
        # Arrange
        # Arrange
        state = create_empty_dialogue_state()
        state["flow_stack"] = [
            {
                "flow_id": "test-123",
                "flow_name": "test_flow",
                "flow_state": FlowContextState.ACTIVE,
                "current_step": None,
                "step_index": 0,
                "outputs": {},
                "started_at": 100.0,
            }
        ]

        # Act
        result = await end_flow_node(
            state, RunnableConfig(configurable={"runtime_context": MagicMock()})
        )

        # Assert
        assert result == {}

    @pytest.mark.asyncio
    async def test_does_not_modify_state(self):
        """
        GIVEN a flow on the stack
        WHEN end_flow_node is called
        THEN state is not modified (resume_node handles stack)
        """
        # Arrange
        # Arrange
        state = create_empty_dialogue_state()
        state["flow_stack"] = [
            {
                "flow_id": "test-123",
                "flow_name": "test_flow",
                "flow_state": FlowContextState.ACTIVE,
                "current_step": None,
                "step_index": 0,
                "outputs": {},
                "started_at": 100.0,
            }
        ]
        original_stack_len = len(state["flow_stack"])

        # Act
        await end_flow_node(state, RunnableConfig(configurable={"runtime_context": MagicMock()}))

        # Assert
        assert len(state["flow_stack"]) == original_stack_len


class TestSubgraphBuilder:
    """Tests for SubgraphBuilder."""

    @pytest.fixture
    def builder(self):
        return SubgraphBuilder()

    def test_build_adds_end_flow_node(self, builder):
        """Builder should add __end_flow__ node to graph."""
        flow_config = FlowConfig(
            description="Test flow",
            steps=[
                SayStepConfig(step="greet", type="say", message="Hello"),
            ],
        )

        graph = builder.build(flow_config)

        # Check that __end_flow__ node is in the graph
        assert END_FLOW_NODE in graph.nodes

    def test_build_empty_flow_includes_end_flow(self, builder):
        """Empty flow should still have __end_flow__ node."""
        flow_config = FlowConfig(
            description="Empty flow",
            steps=[],
        )

        graph = builder.build(flow_config)

        assert END_FLOW_NODE in graph.nodes

    def test_build_creates_nodes_for_steps(self, builder):
        """Builder should create a node for each step."""
        flow_config = FlowConfig(
            description="Test flow",
            steps=[
                SayStepConfig(step="step1", type="say", message="One"),
                SayStepConfig(step="step2", type="say", message="Two"),
            ],
        )

        graph = builder.build(flow_config)

        assert "step1" in graph.nodes
        assert "step2" in graph.nodes
        assert END_FLOW_NODE in graph.nodes
