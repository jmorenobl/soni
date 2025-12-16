"""Unit tests for SubgraphBuilder and end_flow_node."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from soni.compiler.subgraph import END_FLOW_NODE, SubgraphBuilder, end_flow_node
from soni.core.config import FlowConfig, StepConfig
from soni.core.state import create_empty_dialogue_state


class TestEndFlowNode:
    """Tests for end_flow_node function."""

    @pytest.mark.asyncio
    async def test_pops_flow_from_stack(self):
        """end_flow_node should pop the completed flow."""
        mock_fm = MagicMock()
        mock_fm.pop_flow = AsyncMock()

        mock_config = {
            "configurable": {
                "runtime_context": MagicMock(flow_manager=mock_fm),
            }
        }

        state = create_empty_dialogue_state()
        # Simulate a flow on the stack
        state["flow_stack"] = [
            {
                "flow_id": "test-123",
                "flow_name": "test_flow",
                "flow_state": "active",
                "current_step": None,
                "step_index": 0,
                "outputs": {},
                "started_at": 100.0,
            }
        ]

        result = await end_flow_node(state, mock_config)

        mock_fm.pop_flow.assert_called_once_with(state, result="completed")
        assert "flow_stack" in result

    @pytest.mark.asyncio
    async def test_sets_flow_state_to_idle_when_stack_empty(self):
        """Should set flow_state to idle when stack becomes empty."""
        mock_fm = MagicMock()
        mock_fm.pop_flow = AsyncMock()

        mock_config = {
            "configurable": {
                "runtime_context": MagicMock(flow_manager=mock_fm),
            }
        }

        state = create_empty_dialogue_state()
        state["flow_stack"] = []  # Empty after pop

        result = await end_flow_node(state, mock_config)

        assert result["flow_state"] == "idle"

    @pytest.mark.asyncio
    async def test_sets_flow_state_to_active_when_stack_has_items(self):
        """Should set flow_state to active when stack still has items."""
        mock_fm = MagicMock()
        mock_fm.pop_flow = AsyncMock()

        mock_config = {
            "configurable": {
                "runtime_context": MagicMock(flow_manager=mock_fm),
            }
        }

        state = create_empty_dialogue_state()
        # Simulate multiple flows on stack
        state["flow_stack"] = [
            {
                "flow_id": "parent-123",
                "flow_name": "parent_flow",
                "flow_state": "active",
                "current_step": None,
                "step_index": 0,
                "outputs": {},
                "started_at": 100.0,
            }
        ]

        result = await end_flow_node(state, mock_config)

        assert result["flow_state"] == "active"


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
                StepConfig(step="greet", type="say", message="Hello"),
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
                StepConfig(step="step1", type="say", message="One"),
                StepConfig(step="step2", type="say", message="Two"),
            ],
        )

        graph = builder.build(flow_config)

        assert "step1" in graph.nodes
        assert "step2" in graph.nodes
        assert END_FLOW_NODE in graph.nodes
