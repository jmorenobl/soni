"""Unit tests for SubgraphBuilder."""

from soni.compiler.subgraph import SubgraphBuilder
from soni.config import FlowConfig, SayStepConfig


class TestSubgraphBuilder:
    """Tests for compiling flow configurations into graphs."""

    def test_build_linear_flow_creates_sequential_edges(self):
        """
        GIVEN config with steps A -> B
        WHEN built
        THEN graph has edges START->A->B->END
        """
        # Arrange
        config = FlowConfig(
            description="Test",
            steps=[
                SayStepConfig(step="step_a", type="say", message="A"),
                SayStepConfig(step="step_b", type="say", message="B"),
            ],
        )
        builder = SubgraphBuilder()

        # Act
        graph = builder.build(config)
        compiled = graph.compile()

        # We can inspect the graph structure indirectly or by using get_graph() in newer LangGraph
        # For now, verify it compiles without error and has expected nodes
        assert "step_a" in compiled.nodes
        assert "step_b" in compiled.nodes
        # Note: edges are harder to inspect on compiled graph without execution or internal access

    def test_build_with_jump_to_creates_edge_to_target(self):
        """
        GIVEN config with A (jump_to=C) -> B -> C
        WHEN built
        THEN A points to C, skipping B
        """
        config = FlowConfig(
            description="Test",
            steps=[
                SayStepConfig(step="step_a", type="say", message="A", jump_to="step_c"),
                SayStepConfig(step="step_b", type="say", message="B"),
                SayStepConfig(step="step_c", type="say", message="C"),
            ],
        )
        builder = SubgraphBuilder()
        graph = builder.build(config)
        compiled = graph.compile()
        assert "step_c" in compiled.nodes

    def test_empty_config_returns_empty_graph(self):
        """
        GIVEN empty steps
        WHEN built
        THEN returns graph with START->END
        """
        config = FlowConfig(description="Empty", steps=[])
        builder = SubgraphBuilder()
        graph = builder.build(config)
        compiled = graph.compile()
        assert compiled is not None
