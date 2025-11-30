"""Tests for jump support in compiler"""

import pytest

from soni.compiler.builder import StepCompiler
from soni.compiler.dag import DAGEdge, DAGNode, FlowDAG, NodeType
from soni.compiler.parser import ParsedStep, StepParser
from soni.core.config import (
    ActionConfig,
    FlowConfig,
    ModelsConfig,
    NLUModelConfig,
    Settings,
    SoniConfig,
    StepConfig,
)
from soni.core.errors import CompilationError


def test_parser_parses_jump_to():
    """Test parser parses jump_to correctly"""
    # Arrange
    parser = StepParser()
    steps = [
        StepConfig(
            step="collect_name",
            type="collect",
            slot="name",
            jump_to="validate_name",
        )
    ]

    # Act
    parsed = parser.parse(steps)

    # Assert
    assert len(parsed) == 1
    assert parsed[0].config.get("jump_to") == "validate_name"


def test_parser_rejects_jump_to_in_branch():
    """Test parser rejects jump_to in branch step"""
    # Arrange
    parser = StepParser()
    steps = [
        StepConfig(
            step="decide",
            type="branch",
            input="status",
            cases={"ok": "continue"},
            jump_to="somewhere",  # Invalid
        )
    ]

    # Act & Assert
    with pytest.raises(CompilationError) as exc_info:
        parser.parse(steps)

    assert "cannot use 'jump_to'" in str(exc_info.value)


def test_compiler_generates_jump_edge():
    """Test compiler generates edge for jump_to"""
    # Arrange
    config = SoniConfig(
        version="1.0",
        settings=Settings(
            models=ModelsConfig(nlu=NLUModelConfig(provider="openai", model="gpt-4o-mini"))
        ),
        flows={
            "test_flow": FlowConfig(
                description="Test",
                steps=[
                    StepConfig(step="start", type="collect", slot="name", jump_to="end"),
                    StepConfig(step="validate", type="action", call="validate"),
                    StepConfig(step="end", type="action", call="finish"),
                ],
            )
        },
        slots={"name": {"type": "string", "prompt": "Name?"}},
        actions={
            "validate": ActionConfig(description="Validate", inputs=[], outputs=[]),
            "finish": ActionConfig(description="Finish", inputs=[], outputs=[]),
        },
    )
    parser = StepParser()
    compiler = StepCompiler(config=config)

    # Create steps with jump
    steps = [
        StepConfig(step="start", type="collect", slot="name", jump_to="end"),
        StepConfig(step="validate", type="action", call="validate"),
        StepConfig(step="end", type="action", call="finish"),
    ]
    parsed_steps = parser.parse(steps)

    # Act
    dag = compiler._generate_dag("test_flow", parsed_steps)

    # Assert
    # Find edge from start to end (jump)
    jump_edge = next(
        (e for e in dag.edges if e.source == "start" and e.target == "end"),
        None,
    )
    assert jump_edge is not None
    # Should not have edge from start to validate (sequential)
    sequential_edge = next(
        (e for e in dag.edges if e.source == "start" and e.target == "validate"),
        None,
    )
    assert sequential_edge is None


def test_compiler_validates_jump_target_exists():
    """Test compiler validates jump_to target exists"""
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

    # Create DAG with invalid jump
    invalid_dag = FlowDAG(
        name="test",
        nodes=[
            DAGNode(
                id="start",
                type=NodeType.COLLECT,
                config={"slot_name": "name", "jump_to": "nonexistent"},
            ),
        ],
        edges=[],
    )

    # Act & Assert
    with pytest.raises(CompilationError) as exc_info:
        compiler._validate_dag(invalid_dag)

    assert (
        "jump_to target" in str(exc_info.value).lower()
        or "not found" in str(exc_info.value).lower()
    )


def test_compiler_handles_loop_with_jump():
    """Test compiler handles loop created with jump_to"""
    # Arrange
    config = SoniConfig(
        version="1.0",
        settings=Settings(
            models=ModelsConfig(nlu=NLUModelConfig(provider="openai", model="gpt-4o-mini"))
        ),
        flows={
            "loop_flow": FlowConfig(
                description="Loop flow",
                steps=[
                    StepConfig(step="collect", type="collect", slot="value"),
                    StepConfig(step="validate", type="action", call="validate"),
                    StepConfig(step="retry", type="action", call="retry", jump_to="collect"),
                ],
            )
        },
        slots={"value": {"type": "string", "prompt": "Value?"}},
        actions={
            "validate": ActionConfig(description="Validate", inputs=[], outputs=[]),
            "retry": ActionConfig(description="Retry", inputs=[], outputs=[]),
        },
    )
    parser = StepParser()
    compiler = StepCompiler(config=config)

    # Create steps with loop (retry jumps back to collect)
    steps = [
        StepConfig(step="collect", type="collect", slot="value"),
        StepConfig(step="validate", type="action", call="validate"),
        StepConfig(step="retry", type="action", call="retry", jump_to="collect"),
    ]
    parsed_steps = parser.parse(steps)

    # Act
    dag = compiler._generate_dag("loop_flow", parsed_steps)

    # Assert
    # Should have edge from retry back to collect
    loop_edge = next(
        (e for e in dag.edges if e.source == "retry" and e.target == "collect"),
        None,
    )
    assert loop_edge is not None
