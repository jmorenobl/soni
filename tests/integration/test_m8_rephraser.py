"""M8: Response Rephraser Integration Tests."""

import dspy
import pytest
from dspy.utils.dummies import DummyLM
from langgraph.checkpoint.memory import MemorySaver

from soni.config.models import (
    FlowConfig,
    SayStepConfig,
    Settings,
    SoniConfig,
)
from soni.runtime.loop import RuntimeLoop


@pytest.fixture(autouse=True)
def configure_dspy_dummy_lm():
    """Configure DummyLM for integration tests."""
    dummy_responses = [
        # Polished responses from rephraser
        {"polished_response": "Hello! I'm here to help you today. What can I do for you?"},
        {"polished_response": "Great to see you! How may I assist you?"},
    ]
    lm = DummyLM(dummy_responses)
    dspy.configure(lm=lm)
    yield


@pytest.mark.asyncio
async def test_rephraser_enabled_polishes_response():
    """With rephraser enabled, responses are polished by LLM."""
    # Arrange
    config = SoniConfig(
        settings=Settings(rephrase_responses=True, rephrase_tone="friendly"),
        flows={
            "main": FlowConfig(
                steps=[
                    SayStepConfig(step="greet", message="Hello", rephrase=True),
                ]
            )
        },
    )
    checkpointer = MemorySaver()

    # Act
    async with RuntimeLoop(config, checkpointer=checkpointer) as runtime:
        response = await runtime.process_message("hi", user_id="u1")

    # Assert - Response should be polished (from DummyLM)
    assert response is not None
    assert len(response) > len("Hello")  # Polished is longer


@pytest.mark.asyncio
async def test_rephraser_disabled_keeps_template():
    """With rephraser disabled, template response is returned as-is."""
    # Arrange
    config = SoniConfig(
        settings=Settings(rephrase_responses=False),  # Disabled
        flows={
            "main": FlowConfig(
                steps=[
                    SayStepConfig(step="greet", message="Hello", rephrase=True),
                ]
            )
        },
    )
    checkpointer = MemorySaver()

    # Act
    async with RuntimeLoop(config, checkpointer=checkpointer) as runtime:
        response = await runtime.process_message("hi", user_id="u2")

    # Assert - Response should be the template
    assert response == "Hello"


@pytest.mark.asyncio
async def test_step_level_rephrase_disabled():
    """Step with rephrase=False keeps template even if global is enabled."""
    # Arrange
    config = SoniConfig(
        settings=Settings(rephrase_responses=True, rephrase_tone="friendly"),
        flows={
            "main": FlowConfig(
                steps=[
                    SayStepConfig(step="greet", message="Hello", rephrase=False),
                ]
            )
        },
    )
    checkpointer = MemorySaver()

    # Act
    async with RuntimeLoop(config, checkpointer=checkpointer) as runtime:
        response = await runtime.process_message("hi", user_id="u3")

    # Assert - Response should be the template (step-level override)
    assert response == "Hello"


@pytest.mark.asyncio
async def test_settings_default_values():
    """Settings have correct default values."""
    # Arrange
    config = SoniConfig(
        flows={
            "main": FlowConfig(
                steps=[
                    SayStepConfig(step="greet", message="Hello"),
                ]
            )
        },
    )

    # Assert - Defaults
    assert config.settings.rephrase_responses is False
    assert config.settings.rephrase_tone == "friendly"
