"""Tests for StepCompiler"""

import pytest
from langgraph.graph import StateGraph

from soni.compiler.builder import StepCompiler
from soni.compiler.parser import ParsedStep
from soni.core.config import SoniConfig
from soni.core.errors import CompilationError
from soni.core.state import (
    DialogueState,
    create_empty_state,
    create_initial_state,
    get_all_slots,
    get_current_flow,
)


@pytest.fixture
def sample_config() -> SoniConfig:
    """Create sample configuration for testing."""
    config_dict = {
        "version": "1.0",
        "settings": {
            "models": {
                "nlu": {
                    "provider": "openai",
                    "model": "gpt-4o-mini",
                    "temperature": 0.1,
                },
            },
        },
        "flows": {
            "test_flow": {
                "description": "Test flow",
                "steps": [
                    {"step": "get_origin", "type": "collect", "slot": "origin"},
                    {"step": "search", "type": "action", "call": "search_flights"},
                ],
            }
        },
        "slots": {
            "origin": {
                "type": "string",
                "prompt": "What is your origin?",
            }
        },
        "actions": {"search_flights": {"inputs": [], "outputs": []}},
    }
    return SoniConfig(**config_dict)


def test_compiler_generates_linear_dag(sample_config: SoniConfig):
    """Test compiler generates linear DAG correctly"""
    # Arrange
    compiler = StepCompiler(config=sample_config)
    parsed_steps = [
        ParsedStep(step_id="get_origin", step_type="collect", config={"slot_name": "origin"}),
        ParsedStep(step_id="search", step_type="action", config={"action_name": "search_flights"}),
    ]

    # Act
    dag = compiler._generate_dag("test_flow", parsed_steps)

    # Assert
    assert len(dag.nodes) == 3  # understand + 2 steps
    assert dag.nodes[0].id == "understand"
    assert dag.nodes[1].id == "get_origin"
    assert dag.nodes[2].id == "search"
    assert (
        len(dag.edges) == 4
    )  # START->understand, understand->get_origin, get_origin->search, search->END
    assert dag.edges[0].source == "__start__"
    assert dag.edges[0].target == "understand"


def test_compiler_validates_unique_node_ids(sample_config: SoniConfig):
    """Test compiler detects duplicate node IDs"""
    # Arrange
    compiler = StepCompiler(config=sample_config)
    parsed_steps = [
        ParsedStep(step_id="duplicate", step_type="collect", config={"slot_name": "origin"}),
        ParsedStep(step_id="duplicate", step_type="action", config={"action_name": "search"}),
    ]

    # Act
    dag = compiler._generate_dag("test_flow", parsed_steps)

    # Assert - validation should catch duplicates
    with pytest.raises(CompilationError) as exc_info:
        compiler._validate_dag(dag)

    assert "duplicate" in str(exc_info.value).lower()


def test_compiler_validates_edge_targets_exist(sample_config: SoniConfig):
    """Test compiler validates that edge targets exist"""
    # Arrange
    compiler = StepCompiler(config=sample_config)
    # Create DAG with invalid edge manually
    from soni.compiler.dag import DAGEdge, DAGNode, FlowDAG, NodeType

    invalid_dag = FlowDAG(
        name="test_flow",
        nodes=[DAGNode(id="understand", type=NodeType.UNDERSTAND, config={})],
        edges=[DAGEdge(source="understand", target="nonexistent")],
    )

    # Act & Assert
    with pytest.raises(CompilationError) as exc_info:
        compiler._validate_dag(invalid_dag)

    assert "not found" in str(exc_info.value).lower()


def test_compiler_builds_valid_graph(sample_config: SoniConfig):
    """Test compiler builds valid LangGraph StateGraph"""
    # Arrange
    compiler = StepCompiler(config=sample_config)
    parsed_steps = [
        ParsedStep(step_id="get_origin", step_type="collect", config={"slot_name": "origin"}),
    ]

    # Act
    graph = compiler.compile("test_flow", parsed_steps)

    # Assert
    assert isinstance(graph, StateGraph)


def test_compiler_handles_empty_steps(sample_config: SoniConfig):
    """Test compiler handles flow with no steps (only understand)"""
    # Arrange
    compiler = StepCompiler(config=sample_config)
    parsed_steps: list[ParsedStep] = []

    # Act
    dag = compiler._generate_dag("test_flow", parsed_steps)

    # Assert
    assert len(dag.nodes) == 1  # Only understand
    assert dag.nodes[0].id == "understand"
    assert len(dag.edges) == 0  # No edges for single node


def test_compiler_validates_entry_point_exists(sample_config: SoniConfig):
    """Test compiler validates entry point exists in DAG"""
    # Arrange
    from soni.compiler.dag import DAGEdge, DAGNode, FlowDAG, NodeType

    compiler = StepCompiler(config=sample_config)
    invalid_dag = FlowDAG(
        name="test",
        nodes=[DAGNode(id="node1", type=NodeType.COLLECT, config={})],
        edges=[],
        entry_point="nonexistent",
    )

    # Act & Assert
    with pytest.raises(CompilationError) as exc_info:
        compiler._validate_dag(invalid_dag)

    assert "entry point" in str(exc_info.value).lower()
    assert "nonexistent" in str(exc_info.value)
