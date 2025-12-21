"""Unit tests for SayNodeFactory."""

from unittest.mock import MagicMock

import pytest
from langgraph.runtime import Runtime

from soni.compiler.nodes.say import SayNodeFactory
from soni.config.models import SayStepConfig
from soni.runtime.context import RuntimeContext


@pytest.mark.asyncio
async def test_say_node_returns_message():
    """Say node returns the configured message."""
    step = SayStepConfig(step="test", message="Test message")
    factory = SayNodeFactory()
    node = factory.create(step)

    # Mock Runtime
    runtime = MagicMock(spec=Runtime)
    # No context needed for say node currently (it doesn't use it yet in M1 simplified version)
    # But just in case
    runtime.context = MagicMock(spec=RuntimeContext)

    result = await node({}, runtime)

    assert result["response"] == "Test message"


def test_say_node_has_correct_name():
    """Say node function has descriptive name."""
    step = SayStepConfig(step="greet", message="Hello")
    factory = SayNodeFactory()
    node = factory.create(step)

    assert node.__name__ == "say_greet"
