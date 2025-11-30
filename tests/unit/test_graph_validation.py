"""Tests for graph validation in compiler"""

import pytest

from soni.compiler.builder import StepCompiler
from soni.compiler.dag import DAGEdge, DAGNode, FlowDAG, NodeType
from soni.core.config import SoniConfig
from soni.core.errors import CompilationError


@pytest.fixture
def compiler() -> StepCompiler:
    """Create compiler instance for testing."""
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
        "flows": {},
        "slots": {},
        "actions": {},
    }
    return StepCompiler(config=SoniConfig(**config_dict))


def test_validate_dag_detects_duplicate_node_ids(compiler: StepCompiler):
    """Test validation detects duplicate node IDs"""
    # Arrange
    dag = FlowDAG(
        name="test",
        nodes=[
            DAGNode(id="duplicate", type=NodeType.COLLECT, config={}),
            DAGNode(id="duplicate", type=NodeType.ACTION, config={}),
        ],
        edges=[],
    )

    # Act & Assert
    with pytest.raises(CompilationError) as exc_info:
        compiler._validate_dag(dag)

    assert "duplicate" in str(exc_info.value).lower()


def test_validate_dag_detects_invalid_edge_source(compiler: StepCompiler):
    """Test validation detects edge with invalid source"""
    # Arrange
    dag = FlowDAG(
        name="test",
        nodes=[DAGNode(id="node1", type=NodeType.COLLECT, config={})],
        edges=[DAGEdge(source="nonexistent", target="node1")],
    )

    # Act & Assert
    with pytest.raises(CompilationError) as exc_info:
        compiler._validate_dag(dag)

    assert "source" in str(exc_info.value).lower()
    assert "not found" in str(exc_info.value).lower()


def test_validate_dag_detects_invalid_edge_target(compiler: StepCompiler):
    """Test validation detects edge with invalid target"""
    # Arrange
    dag = FlowDAG(
        name="test",
        nodes=[DAGNode(id="node1", type=NodeType.COLLECT, config={})],
        edges=[DAGEdge(source="node1", target="nonexistent")],
    )

    # Act & Assert
    with pytest.raises(CompilationError) as exc_info:
        compiler._validate_dag(dag)

    assert "target" in str(exc_info.value).lower()
    assert "not found" in str(exc_info.value).lower()


def test_validate_dag_allows_start_and_end_special_nodes(compiler: StepCompiler):
    """Test validation allows __start__ and __end__ in edges"""
    # Arrange
    dag = FlowDAG(
        name="test",
        nodes=[DAGNode(id="node1", type=NodeType.COLLECT, config={})],
        edges=[
            DAGEdge(source="__start__", target="node1"),
            DAGEdge(source="node1", target="__end__"),
        ],
        entry_point="node1",  # Set entry point to existing node
    )

    # Act & Assert (should not raise)
    compiler._validate_dag(dag)  # Should pass


def test_validate_dag_validates_entry_point(compiler: StepCompiler):
    """Test validation checks that entry point exists"""
    # Arrange
    dag = FlowDAG(
        name="test",
        nodes=[DAGNode(id="node1", type=NodeType.COLLECT, config={})],
        edges=[],
        entry_point="nonexistent",
    )

    # Act & Assert
    with pytest.raises(CompilationError) as exc_info:
        compiler._validate_dag(dag)

    assert "entry point" in str(exc_info.value).lower()
