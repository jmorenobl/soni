"""Tests for ActionRegistry integration with compiler."""

from pathlib import Path

import pytest
import yaml

from soni.actions.registry import ActionRegistry
from soni.compiler.flow_compiler import FlowCompiler
from soni.core.config import SoniConfig


@pytest.mark.integration
@pytest.mark.asyncio
async def test_compiler_uses_action_registry():
    """Test that compiler uses ActionRegistry for actions"""
    # Arrange
    ActionRegistry.clear()

    @ActionRegistry.register("test_action")
    async def test_handler(param: str) -> dict:
        return {"result": param}

    config_dict = {
        "version": "1.0",
        "settings": {"models": {"nlu": {"provider": "openai", "model": "gpt-4o-mini"}}},
        "flows": {
            "test_flow": {
                "description": "Test flow for action registry",
                "process": [{"step": "action_step", "type": "action", "call": "test_action"}],
            }
        },
        "actions": {"test_action": {"inputs": ["param"], "outputs": ["result"]}},
    }
    config = SoniConfig(**config_dict)
    compiler = FlowCompiler(config)

    # Act
    graph = compiler.compile_flow("test_flow")

    # Assert
    assert graph is not None
    # Verify action is registered
    assert ActionRegistry.is_registered("test_action")


def test_yaml_no_contains_handler_paths():
    """Test that YAML examples don't contain handler paths"""
    # Arrange
    yaml_files = list(Path("examples").rglob("*.yaml"))

    # Act & Assert
    for yaml_file in yaml_files:
        with open(yaml_file) as f:
            content = yaml.safe_load(f)
            if "actions" in content:
                for action_name, action_config in content["actions"].items():
                    assert "handler" not in action_config, (
                        f"YAML {yaml_file} contains 'handler' field in action '{action_name}'. "
                        f"Use @ActionRegistry.register() instead."
                    )


@pytest.mark.integration
@pytest.mark.asyncio
async def test_auto_discovery_imports_actions():
    """Test that auto-discovery imports actions correctly"""
    # Arrange
    import importlib.util
    import tempfile
    from pathlib import Path

    ActionRegistry.clear()

    # Create temporary actions.py
    with tempfile.TemporaryDirectory() as tmpdir:
        actions_file = Path(tmpdir) / "actions.py"
        actions_file.write_text(
            """
from soni.actions.registry import ActionRegistry

@ActionRegistry.register("auto_discovered_action")
async def auto_action() -> dict:
    return {"result": "ok"}
"""
        )

        # Act - Import the module
        spec = importlib.util.spec_from_file_location("user_actions", actions_file)
        if spec and spec.loader:
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)

        # Assert
        assert ActionRegistry.is_registered("auto_discovered_action")
