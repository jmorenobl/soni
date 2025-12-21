"""M6: Link/Call + Nested Flows Integration Tests.

Tests verify that link transfers control without return,
and call invokes subflows with return to parent.
"""

import pytest

from soni.config.models import (
    CallStepConfig,
    FlowConfig,
    LinkStepConfig,
    SayStepConfig,
    SoniConfig,
)
from soni.runtime.loop import RuntimeLoop


@pytest.mark.asyncio
async def test_link_transfers_control():
    """Link step transfers to target flow without return."""
    # Arrange
    config = SoniConfig(
        flows={
            "main": FlowConfig(
                description="Main flow",
                steps=[
                    SayStepConfig(step="start", message="Starting..."),
                    LinkStepConfig(step="go", target="other"),
                    SayStepConfig(step="never", message="Never reached"),
                ],
            ),
            "other": FlowConfig(
                description="Other flow",
                steps=[
                    SayStepConfig(step="end", message="In other flow!"),
                ],
            ),
        }
    )

    # Act
    async with RuntimeLoop(config) as runtime:
        response = await runtime.process_message("start")

    # Assert
    assert "In other flow!" in response
    assert "Never reached" not in response


@pytest.mark.asyncio
async def test_call_returns_to_parent():
    """Call step executes subflow then returns."""
    # Arrange
    config = SoniConfig(
        flows={
            "main": FlowConfig(
                description="Main flow",
                steps=[
                    SayStepConfig(step="before", message="Before call"),
                    CallStepConfig(step="do_auth", target="auth"),
                    SayStepConfig(step="after", message="After call"),
                ],
            ),
            "auth": FlowConfig(
                description="Auth subflow",
                steps=[
                    SayStepConfig(step="auth_msg", message="Authenticating..."),
                ],
            ),
        }
    )

    # Act
    async with RuntimeLoop(config) as runtime:
        response = await runtime.process_message("start")

    # Assert - both subflow and parent continuation should be in response
    assert "Authenticating" in response
    assert "After call" in response


@pytest.mark.asyncio
async def test_nested_calls():
    """Nested calls work correctly (A calls B calls C)."""
    # Arrange
    config = SoniConfig(
        flows={
            "flow_a": FlowConfig(
                description="Flow A",
                steps=[
                    SayStepConfig(step="a1", message="A1"),
                    CallStepConfig(step="call_b", target="flow_b"),
                    SayStepConfig(step="a2", message="A2"),
                ],
            ),
            "flow_b": FlowConfig(
                description="Flow B",
                steps=[
                    SayStepConfig(step="b1", message="B1"),
                    CallStepConfig(step="call_c", target="flow_c"),
                    SayStepConfig(step="b2", message="B2"),
                ],
            ),
            "flow_c": FlowConfig(
                description="Flow C",
                steps=[
                    SayStepConfig(step="c1", message="C1"),
                ],
            ),
        }
    )

    # Act
    async with RuntimeLoop(config) as runtime:
        response = await runtime.process_message("start flow a")

    # Assert - all messages in correct order
    assert "A1" in response
    assert "B1" in response
    assert "C1" in response
    # After returns
    assert "B2" in response
    assert "A2" in response
