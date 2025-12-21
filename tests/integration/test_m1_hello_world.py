"""M1: Hello World integration test."""

import pytest

from soni.config.models import SoniConfig, FlowConfig, SayStepConfig
from soni.runtime.loop import RuntimeLoop


@pytest.mark.asyncio
async def test_hello_world():
    """A flow with a single say step returns the message."""
    # Arrange
    config = SoniConfig(
        flows={
            "greet": FlowConfig(
                steps=[SayStepConfig(step="hello", message="Hello, World!")]
            )
        }
    )
    
    # Act
    async with RuntimeLoop(config) as runtime:
        response = await runtime.process_message("hi")
    
    # Assert
    assert response == "Hello, World!"


@pytest.mark.asyncio
async def test_multi_step_say():
    """A flow with multiple say steps returns the last message."""
    # Arrange
    config = SoniConfig(
        flows={
            "greet": FlowConfig(
                steps=[
                    SayStepConfig(step="hello", message="Hello!"),
                    SayStepConfig(step="welcome", message="Welcome to Soni!"),
                ]
            )
        }
    )
    
    # Act
    async with RuntimeLoop(config) as runtime:
        response = await runtime.process_message("hi")
    
    # Assert
    assert response == "Welcome to Soni!"
