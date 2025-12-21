"""M1: Hello World integration test (M4 - NLU-driven)."""

import pytest

from soni.config.models import FlowConfig, SayStepConfig, SoniConfig
from soni.runtime.loop import RuntimeLoop


@pytest.mark.asyncio
async def test_hello_world():
    """A flow with a single say step returns the message.

    NLU detects intent from flow description and triggers the flow.
    """
    # Arrange - flow with description for NLU to match
    config = SoniConfig(
        flows={
            "greet": FlowConfig(
                description="Greet the user and say hello",
                steps=[SayStepConfig(step="hello", message="Hello, World!")]
            )
        }
    )

    # Act - user message that matches "greet" intent
    async with RuntimeLoop(config) as runtime:
        response = await runtime.process_message("I want to be greeted")

    # Assert
    assert "Hello, World!" in response


@pytest.mark.asyncio
async def test_multi_step_say():
    """A flow with multiple say steps returns the last message."""
    # Arrange
    config = SoniConfig(
        flows={
            "welcome": FlowConfig(
                description="Welcome user to the system",
                steps=[
                    SayStepConfig(step="hello", message="Hello!"),
                    SayStepConfig(step="welcome", message="Welcome to Soni!"),
                ]
            )
        }
    )

    # Act
    async with RuntimeLoop(config) as runtime:
        response = await runtime.process_message("Welcome me please")

    # Assert
    assert "Welcome to Soni!" in response

