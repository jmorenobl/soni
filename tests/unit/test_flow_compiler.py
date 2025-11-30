"""Tests for FlowCompiler"""

from pathlib import Path

import pytest

from soni.compiler.dag import NodeType
from soni.compiler.flow_compiler import FlowCompiler
from soni.core.config import SoniConfig


def test_compiler_creates_dag_with_nodes():
    """Test compiler creates DAG with correct nodes"""
    # Arrange
    config_path = Path("examples/flight_booking/soni.yaml")
    config = SoniConfig.from_yaml(config_path)
    compiler = FlowCompiler(config)

    # Act
    dag = compiler.compile_flow("book_flight")

    # Assert
    assert len(dag.nodes) > 1  # At least understand + steps
    assert dag.nodes[0].type == NodeType.UNDERSTAND
    assert dag.nodes[0].id == "understand"
    # Check that subsequent nodes are collect or action
    for node in dag.nodes[1:]:
        assert node.type in (NodeType.COLLECT, NodeType.ACTION)


def test_compiler_creates_sequential_edges():
    """Test compiler connects nodes sequentially"""
    # Arrange
    config_path = Path("examples/flight_booking/soni.yaml")
    config = SoniConfig.from_yaml(config_path)
    compiler = FlowCompiler(config)

    # Act
    dag = compiler.compile_flow("book_flight")

    # Assert
    assert len(dag.edges) > 0
    # First edge should be START -> understand
    assert dag.edges[0].source == "__start__"
    assert dag.edges[0].target == "understand"
    # Last edge should be last node -> END
    assert dag.edges[-1].target == "__end__"
    # Middle edges should connect nodes sequentially
    # Edge i connects node i-1 to node i (after START edge)
    for i in range(1, len(dag.edges) - 1):
        assert dag.edges[i].source == dag.nodes[i - 1].id
        assert dag.edges[i].target == dag.nodes[i].id


def test_compiler_raises_on_missing_flow():
    """Test compiler raises KeyError for missing flow"""
    # Arrange
    config_path = Path("examples/flight_booking/soni.yaml")
    config = SoniConfig.from_yaml(config_path)
    compiler = FlowCompiler(config)

    # Act & Assert
    with pytest.raises(KeyError) as exc_info:
        compiler.compile_flow("nonexistent_flow")

    assert "nonexistent_flow" in str(exc_info.value)


def test_compiler_creates_collect_node():
    """Test compiler creates collect node with correct config"""
    # Arrange
    config_path = Path("examples/flight_booking/soni.yaml")
    config = SoniConfig.from_yaml(config_path)
    compiler = FlowCompiler(config)

    # Act
    dag = compiler.compile_flow("book_flight")

    # Assert
    collect_nodes = [n for n in dag.nodes if n.type == NodeType.COLLECT]
    assert len(collect_nodes) > 0
    for node in collect_nodes:
        assert "slot_name" in node.config
        assert isinstance(node.config["slot_name"], str)


def test_compiler_creates_action_node():
    """Test compiler creates action node with correct config"""
    # Arrange
    config_path = Path("examples/flight_booking/soni.yaml")
    config = SoniConfig.from_yaml(config_path)
    compiler = FlowCompiler(config)

    # Act
    dag = compiler.compile_flow("book_flight")

    # Assert
    action_nodes = [n for n in dag.nodes if n.type == NodeType.ACTION]
    if len(action_nodes) > 0:
        for node in action_nodes:
            assert "action_name" in node.config
            assert isinstance(node.config["action_name"], str)
            assert "map_outputs" in node.config
            assert isinstance(node.config["map_outputs"], dict)


def test_compiler_dag_has_correct_structure():
    """Test DAG has correct structure with entry point"""
    # Arrange
    config_path = Path("examples/flight_booking/soni.yaml")
    config = SoniConfig.from_yaml(config_path)
    compiler = FlowCompiler(config)

    # Act
    dag = compiler.compile_flow("book_flight")

    # Assert
    assert dag.name == "book_flight"
    assert dag.entry_point == "understand"
    assert len(dag.nodes) > 0
    assert len(dag.edges) > 0
    # Verify entry point node exists
    entry_node = next((n for n in dag.nodes if n.id == dag.entry_point), None)
    assert entry_node is not None
    assert entry_node.type == NodeType.UNDERSTAND
