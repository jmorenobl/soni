"""Tests for branch support in compiler"""

import pytest

from soni.compiler.builder import StepCompiler
from soni.compiler.dag import NodeType
from soni.compiler.parser import ParsedStep, StepParser
from soni.core.config import FlowConfig, SoniConfig, StepConfig
from soni.core.errors import CompilationError


def test_parser_parses_branch_step():
    """Test parser parses branch step correctly"""
    # Arrange
    parser = StepParser()
    steps = [
        StepConfig(
            step="decide_path",
            type="branch",
            input="status",
            cases={"success": "continue", "error": "jump_to_error"},
        )
    ]

    # Act
    parsed = parser.parse(steps)

    # Assert
    assert len(parsed) == 1
    assert parsed[0].step_type == "branch"
    assert parsed[0].config["input"] == "status"
    assert parsed[0].config["cases"] == {"success": "continue", "error": "jump_to_error"}


def test_parser_rejects_branch_without_input():
    """Test parser rejects branch step without input"""
    # Arrange
    parser = StepParser()
    steps = [StepConfig(step="decide", type="branch", input=None, cases={"a": "b"})]

    # Act & Assert
    with pytest.raises(CompilationError) as exc_info:
        parser.parse(steps)

    assert "must specify an 'input'" in str(exc_info.value)


def test_parser_rejects_branch_without_cases():
    """Test parser rejects branch step without cases"""
    # Arrange
    parser = StepParser()
    steps = [StepConfig(step="decide", type="branch", input="status", cases=None)]

    # Act & Assert
    with pytest.raises(CompilationError) as exc_info:
        parser.parse(steps)

    assert "must specify 'cases'" in str(exc_info.value)


def test_compiler_generates_branch_node():
    """Test compiler generates branch DAG node"""
    # Arrange
    from soni.core.config import ModelsConfig, NLUModelConfig, Settings

    config = SoniConfig(
        version="1.0",
        settings=Settings(
            models=ModelsConfig(nlu=NLUModelConfig(provider="openai", model="gpt-4o-mini"))
        ),
        flows={},
        slots={},
        actions={},
    )
    compiler = StepCompiler(config=config)
    parsed = ParsedStep(
        step_id="decide",
        step_type="branch",
        config={"input": "status", "cases": {"ok": "continue"}},
    )

    # Act
    node = compiler._parsed_to_dag_node(parsed)

    # Assert
    assert node.type == NodeType.BRANCH
    assert node.config["input"] == "status"
    assert node.config["cases"] == {"ok": "continue"}


def test_compiler_handles_branch_in_flow():
    """Test compiler handles branch step in linear flow"""
    # Arrange
    from soni.core.config import ActionConfig, ModelsConfig, NLUModelConfig, Settings

    config = SoniConfig(
        version="1.0",
        settings=Settings(
            models=ModelsConfig(nlu=NLUModelConfig(provider="openai", model="gpt-4o-mini"))
        ),
        flows={
            "test_flow": FlowConfig(
                description="Test",
                steps=[
                    StepConfig(step="check", type="action", call="check_status"),
                    StepConfig(
                        step="decide",
                        type="branch",
                        input="status",
                        cases={"ok": "continue", "error": "jump_to_error"},
                    ),
                    StepConfig(step="success", type="action", call="handle_success"),
                ],
            )
        },
        slots={},
        actions={
            "check_status": ActionConfig(description="Check", inputs=[], outputs=[]),
            "handle_success": ActionConfig(description="Handle", inputs=[], outputs=[]),
        },
    )
    parser = StepParser()
    compiler = StepCompiler(config=config)
    flow_config = config.flows["test_flow"]
    parsed_steps = parser.parse(flow_config.steps)

    # Act
    dag = compiler._generate_dag("test_flow", parsed_steps)

    # Assert
    branch_node = next(node for node in dag.nodes if node.id == "decide")
    assert branch_node.type == NodeType.BRANCH
    # Branch should not have sequential edge to next node
    # (conditional edge will be added in _build_graph)
