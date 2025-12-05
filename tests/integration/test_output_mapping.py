"""Tests for output mapping in action nodes."""

import pytest

from soni.actions.registry import ActionRegistry
from soni.compiler.builder import StepCompiler
from soni.compiler.parser import StepParser
from soni.core.config import ActionConfig, SoniConfig
from soni.core.state import (
    DialogueState,
    RuntimeContext,
    create_empty_state,
    create_initial_state,
    create_runtime_context,
    get_all_slots,
    get_current_flow,
    get_slot,
    push_flow,
    set_slot,
)
from soni.dm.nodes.factories import create_action_node_factory


@pytest.mark.integration
@pytest.mark.asyncio
async def test_action_node_applies_map_outputs():
    """Test that action node applies map_outputs correctly"""
    # Arrange
    ActionRegistry.clear()

    @ActionRegistry.register("test_action")
    async def test_action(param: str) -> dict:
        return {
            "api_result": "success",
            "api_data": {"key": "value"},
            "api_metadata": "ignored",
        }

    action_config = ActionConfig(
        inputs=["param"],
        outputs=["api_result", "api_data", "api_metadata"],
    )
    config = SoniConfig(
        version="1.0",
        settings={"models": {"nlu": {"provider": "openai", "model": "gpt-4o-mini"}}},
        actions={"test_action": action_config},
        flows={},
        slots={},
    )

    from soni.actions.base import ActionHandler
    from soni.core.scope import ScopeManager
    from soni.du.normalizer import SlotNormalizer

    action_handler = ActionHandler(config)
    context = create_runtime_context(
        config=config,
        scope_manager=ScopeManager(config=config),
        normalizer=SlotNormalizer(config=config),
        action_handler=action_handler,
        du=None,
    )

    map_outputs = {
        "result": "api_result",
        "data": "api_data",
    }

    factory = create_action_node_factory(
        action_name="test_action",
        context=context,
        map_outputs=map_outputs,
    )

    # Create state with new schema
    state = create_empty_state()
    push_flow(state, "test_flow")
    set_slot(state, "param", "test")

    # Act
    updates = await factory(state)

    # Assert
    # With map_outputs, slots are mapped to new names
    # Check flow_slots after applying updates (merge updates into state)
    final_state = state.copy()
    if "flow_slots" in updates:
        final_state["flow_slots"] = updates["flow_slots"]

    assert get_slot(final_state, "result") == "success"
    assert get_slot(final_state, "data") == {"key": "value"}
    # Original output names should not be in slots (mapped)
    assert get_slot(final_state, "api_metadata") is None  # Not mapped
    assert get_slot(final_state, "api_result") is None  # Mapped to "result"
    assert get_slot(final_state, "api_data") is None  # Mapped to "data"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_action_node_without_map_outputs():
    """Test backward compatibility when map_outputs is None"""
    # Arrange
    ActionRegistry.clear()

    @ActionRegistry.register("simple_action")
    async def simple_action() -> dict:
        return {"output1": "value1", "output2": "value2"}

    action_config = ActionConfig(
        inputs=[],
        outputs=["output1", "output2"],
    )
    config = SoniConfig(
        version="1.0",
        settings={"models": {"nlu": {"provider": "openai", "model": "gpt-4o-mini"}}},
        actions={"simple_action": action_config},
        flows={},
        slots={},
    )

    from soni.actions.base import ActionHandler
    from soni.core.scope import ScopeManager
    from soni.du.normalizer import SlotNormalizer

    action_handler = ActionHandler(config)
    context = create_runtime_context(
        config=config,
        scope_manager=ScopeManager(config=config),
        normalizer=SlotNormalizer(config=config),
        action_handler=action_handler,
        du=None,
    )

    factory = create_action_node_factory(
        action_name="simple_action",
        context=context,
        map_outputs=None,  # No mapping
    )

    # Create state with new schema
    state = create_empty_state()
    push_flow(state, "test_flow")

    # Act
    updates = await factory(state)

    # Assert
    # Without map_outputs, all action outputs go to slots directly
    final_state = state.copy()
    if "flow_slots" in updates:
        final_state["flow_slots"] = updates["flow_slots"]

    assert get_slot(final_state, "output1") == "value1"
    assert get_slot(final_state, "output2") == "value2"


def test_validate_map_outputs():
    """Test validation of map_outputs against action outputs"""
    from soni.core.errors import CompilationError

    # Arrange
    action_config = ActionConfig(
        inputs=[],
        outputs=["api_result", "api_data"],
    )
    config = SoniConfig(
        version="1.0",
        settings={"models": {"nlu": {"provider": "openai", "model": "gpt-4o-mini"}}},
        actions={"test_action": action_config},
        flows={
            "test_flow": {
                "description": "Test flow",
                "process": [
                    {
                        "step": "action_step",
                        "type": "action",
                        "call": "test_action",
                        "map_outputs": {
                            "result": "api_result",
                            "unknown": "api_unknown",  # Not in outputs
                        },
                    }
                ],
            }
        },
        slots={},
    )

    parser = StepParser()
    compiler = StepCompiler(config)

    # Act & Assert - Should raise CompilationError
    parsed_steps = parser.parse(config.flows["test_flow"].process)
    dag = compiler._generate_dag("test_flow", parsed_steps)

    with pytest.raises(CompilationError, match="invalid output fields"):
        compiler._validate_dag(dag)
