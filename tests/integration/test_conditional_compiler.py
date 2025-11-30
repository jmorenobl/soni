"""Integration tests for conditional step compiler"""

import pytest
from langgraph.graph import StateGraph

from soni.compiler.builder import StepCompiler
from soni.compiler.parser import StepParser
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
from soni.core.state import DialogueState


@pytest.fixture
def conditional_config() -> SoniConfig:
    """Create configuration with conditional flows."""
    return SoniConfig(
        version="1.0",
        settings=Settings(
            models=ModelsConfig(nlu=NLUModelConfig(provider="openai", model="gpt-4o-mini"))
        ),
        flows={
            "modify_booking": FlowConfig(
                description="Modify booking with branches",
                steps=[
                    StepConfig(step="request_id", type="collect", slot="booking_ref"),
                    StepConfig(
                        step="verify_status",
                        type="action",
                        call="check_booking_rules",
                        map_outputs={"status": "api_status"},
                    ),
                    StepConfig(
                        step="decide_path",
                        type="branch",
                        input="api_status",
                        cases={
                            "modifiable": "continue",
                            "not_modifiable": "jump_to_explain",
                            "not_found": "jump_to_error",
                        },
                    ),
                    StepConfig(step="apply_changes", type="action", call="modify_booking"),
                    StepConfig(step="explain", type="action", call="explain_rejection"),
                    StepConfig(step="error", type="action", call="handle_error"),
                ],
            )
        },
        slots={"booking_ref": {"type": "string", "prompt": "Booking ref?"}},
        actions={
            "check_booking_rules": ActionConfig(description="Check", inputs=[], outputs=["status"]),
            "modify_booking": ActionConfig(description="Modify", inputs=[], outputs=[]),
            "explain_rejection": ActionConfig(description="Explain", inputs=[], outputs=[]),
            "handle_error": ActionConfig(description="Handle", inputs=[], outputs=[]),
        },
    )


def test_compile_flow_with_branches(conditional_config: SoniConfig):
    """Test compiling flow with branch steps"""
    # Arrange
    parser = StepParser()
    compiler = StepCompiler(config=conditional_config)
    flow_config = conditional_config.flows["modify_booking"]

    # Act
    parsed_steps = parser.parse(flow_config.steps)
    graph = compiler.compile("modify_booking", parsed_steps)

    # Assert
    assert len(parsed_steps) == 6
    assert isinstance(graph, StateGraph)

    # Verify branch step was parsed
    branch_step = next(s for s in parsed_steps if s.step_type == "branch")
    assert branch_step.step_id == "decide_path"
    assert branch_step.config["input"] == "api_status"
    assert "modifiable" in branch_step.config["cases"]


def test_compile_flow_with_jumps():
    """Test compiling flow with jump_to"""
    # Arrange
    config = SoniConfig(
        version="1.0",
        settings=Settings(
            models=ModelsConfig(nlu=NLUModelConfig(provider="openai", model="gpt-4o-mini"))
        ),
        flows={
            "retry_flow": FlowConfig(
                description="Flow with retry loop",
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
    flow_config = config.flows["retry_flow"]

    # Act
    parsed_steps = parser.parse(flow_config.steps)
    dag = compiler._generate_dag("retry_flow", parsed_steps)

    # Assert
    # Should have edge from retry to collect (jump)
    jump_edge = next(
        (e for e in dag.edges if e.source == "retry" and e.target == "collect"),
        None,
    )
    assert jump_edge is not None
    # Should not have sequential edge from retry to END
    sequential_to_end = next(
        (e for e in dag.edges if e.source == "retry" and e.target == "__end__"),
        None,
    )
    assert sequential_to_end is None


def test_compile_flow_with_branches_and_jumps():
    """Test compiling flow with both branches and jumps"""
    # Arrange
    config = SoniConfig(
        version="1.0",
        settings=Settings(
            models=ModelsConfig(nlu=NLUModelConfig(provider="openai", model="gpt-4o-mini"))
        ),
        flows={
            "complex_flow": FlowConfig(
                description="Complex flow with branches and jumps",
                steps=[
                    StepConfig(step="start", type="collect", slot="input"),
                    StepConfig(
                        step="check",
                        type="branch",
                        input="input",
                        cases={"valid": "continue", "invalid": "jump_to_retry"},
                    ),
                    StepConfig(step="process", type="action", call="process"),
                    StepConfig(step="retry", type="action", call="retry", jump_to="start"),
                ],
            )
        },
        slots={"input": {"type": "string", "prompt": "Input?"}},
        actions={
            "process": ActionConfig(description="Process", inputs=[], outputs=[]),
            "retry": ActionConfig(description="Retry", inputs=[], outputs=[]),
        },
    )
    parser = StepParser()
    compiler = StepCompiler(config=config)
    flow_config = config.flows["complex_flow"]

    # Act
    parsed_steps = parser.parse(flow_config.steps)
    graph = compiler.compile("complex_flow", parsed_steps)

    # Assert
    assert isinstance(graph, StateGraph)
    assert len(parsed_steps) == 4


def test_compiler_rejects_invalid_branch_target():
    """Test compiler rejects branch with invalid target"""
    # Arrange
    config = SoniConfig(
        version="1.0",
        settings=Settings(
            models=ModelsConfig(nlu=NLUModelConfig(provider="openai", model="gpt-4o-mini"))
        ),
        flows={
            "invalid_flow": FlowConfig(
                description="Flow with invalid branch target",
                steps=[
                    StepConfig(
                        step="branch",
                        type="branch",
                        input="status",
                        cases={"ok": "nonexistent"},
                    ),
                ],
            )
        },
        slots={},
        actions={},
    )
    parser = StepParser()
    compiler = StepCompiler(config=config)
    flow_config = config.flows["invalid_flow"]

    # Act
    parsed_steps = parser.parse(flow_config.steps)

    # Assert
    with pytest.raises(CompilationError) as exc_info:
        compiler.compile("invalid_flow", parsed_steps)

    assert (
        "invalid targets" in str(exc_info.value).lower()
        or "not found" in str(exc_info.value).lower()
    )


def test_compiler_rejects_invalid_jump_target():
    """Test compiler rejects jump_to with invalid target"""
    # Arrange
    config = SoniConfig(
        version="1.0",
        settings=Settings(
            models=ModelsConfig(nlu=NLUModelConfig(provider="openai", model="gpt-4o-mini"))
        ),
        flows={
            "invalid_flow": FlowConfig(
                description="Flow with invalid jump target",
                steps=[
                    StepConfig(step="start", type="collect", slot="value", jump_to="nonexistent"),
                ],
            )
        },
        slots={"value": {"type": "string", "prompt": "Value?"}},
        actions={},
    )
    parser = StepParser()
    compiler = StepCompiler(config=config)
    flow_config = config.flows["invalid_flow"]

    # Act
    parsed_steps = parser.parse(flow_config.steps)

    # Assert
    with pytest.raises(CompilationError) as exc_info:
        compiler.compile("invalid_flow", parsed_steps)

    assert (
        "invalid targets" in str(exc_info.value).lower()
        or "not found" in str(exc_info.value).lower()
    )


def test_compiler_handles_multiple_branches():
    """Test compiler handles flow with multiple branch steps"""
    # Arrange
    config = SoniConfig(
        version="1.0",
        settings=Settings(
            models=ModelsConfig(nlu=NLUModelConfig(provider="openai", model="gpt-4o-mini"))
        ),
        flows={
            "multi_branch_flow": FlowConfig(
                description="Flow with multiple branches",
                steps=[
                    StepConfig(step="start", type="collect", slot="input1"),
                    StepConfig(
                        step="branch1",
                        type="branch",
                        input="input1",
                        cases={"a": "continue", "b": "jump_to_end"},
                    ),
                    StepConfig(step="middle", type="action", call="middle"),
                    StepConfig(
                        step="branch2",
                        type="branch",
                        input="input2",
                        cases={"x": "continue", "y": "jump_to_start"},
                    ),
                    StepConfig(step="end", type="action", call="end"),
                ],
            )
        },
        slots={"input1": {"type": "string", "prompt": "Input1?"}},
        actions={
            "middle": ActionConfig(description="Middle", inputs=[], outputs=[]),
            "end": ActionConfig(description="End", inputs=[], outputs=[]),
        },
    )
    parser = StepParser()
    compiler = StepCompiler(config=config)
    flow_config = config.flows["multi_branch_flow"]

    # Act
    parsed_steps = parser.parse(flow_config.steps)
    graph = compiler.compile("multi_branch_flow", parsed_steps)

    # Assert
    assert isinstance(graph, StateGraph)
    branch_steps = [s for s in parsed_steps if s.step_type == "branch"]
    assert len(branch_steps) == 2
