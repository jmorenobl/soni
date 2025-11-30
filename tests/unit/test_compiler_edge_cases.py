"""Edge case tests for step compiler"""

import pytest

from soni.compiler.builder import StepCompiler
from soni.compiler.parser import ParsedStep, StepParser
from soni.core.config import SoniConfig
from soni.core.errors import CompilationError


def test_parser_handles_empty_steps_list():
    """Test parser handles empty steps list"""
    # Arrange
    parser = StepParser()

    # Act
    parsed = parser.parse([])

    # Assert
    assert len(parsed) == 0


def test_compiler_handles_single_collect_step():
    """Test compiler handles flow with single collect step"""
    # Arrange
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
            "simple": {
                "description": "Simple flow",
                "steps": [{"step": "get_name", "type": "collect", "slot": "name"}],
            }
        },
        "slots": {
            "name": {
                "type": "string",
                "prompt": "What is your name?",
            }
        },
        "actions": {},
    }
    config = SoniConfig(**config_dict)
    parser = StepParser()
    compiler = StepCompiler(config=config)
    flow_config = config.flows["simple"]
    parsed_steps = parser.parse(flow_config.steps)

    # Act
    dag = compiler._generate_dag("simple", parsed_steps)

    # Assert
    assert len(dag.nodes) == 2  # understand + get_name
    assert len(dag.edges) == 3  # START->understand, understand->get_name, get_name->END


def test_compiler_handles_long_linear_flow():
    """Test compiler handles flow with many steps"""
    # Arrange
    steps = [{"step": f"step_{i}", "type": "collect", "slot": f"slot_{i}"} for i in range(10)]
    slots = {
        f"slot_{i}": {
            "type": "string",
            "prompt": f"What is slot {i}?",
        }
        for i in range(10)
    }
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
        "flows": {"long_flow": {"description": "Long flow", "steps": steps}},
        "slots": slots,
        "actions": {},
    }
    config = SoniConfig(**config_dict)
    parser = StepParser()
    compiler = StepCompiler(config=config)
    flow_config = config.flows["long_flow"]
    parsed_steps = parser.parse(flow_config.steps)

    # Act
    dag = compiler._generate_dag("long_flow", parsed_steps)

    # Assert
    assert len(dag.nodes) == 11  # understand + 10 steps
    assert len(dag.edges) == 12  # START->understand, 10 intermediate, last->END


def test_compiler_validates_entry_point_exists():
    """Test compiler validates entry point exists in DAG"""
    # Arrange
    from soni.compiler.dag import DAGEdge, DAGNode, FlowDAG, NodeType

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
    compiler = StepCompiler(config=SoniConfig(**config_dict))
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
