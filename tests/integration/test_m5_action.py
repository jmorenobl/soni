"""M5: Action + Validation Integration Tests.

Tests verify that actions execute correctly, map outputs to slots,
and are idempotent per ADR-002.
"""

import pytest

from soni.actions.registry import ActionRegistry
from soni.config.models import ActionStepConfig, FlowConfig, SayStepConfig, SoniConfig
from soni.runtime.loop import RuntimeLoop


@pytest.mark.asyncio
async def test_action_executes_and_maps_outputs():
    """Action executes and maps outputs to slots."""
    # Arrange
    async def mock_balance(slots: dict) -> dict:
        return {"balance": 1234.56, "currency": "USD"}

    registry = ActionRegistry()
    registry.register("get_balance", mock_balance)

    config = SoniConfig(
        flows={
            "check_balance": FlowConfig(
                description="Check account balance",
                steps=[
                    ActionStepConfig(
                        step="fetch",
                        call="get_balance",
                        map_outputs={"balance": "account_balance"},
                    ),
                    SayStepConfig(step="show", message="Your balance is ${account_balance}"),
                ],
            )
        }
    )

    # Act
    async with RuntimeLoop(config, action_registry=registry) as runtime:
        response = await runtime.process_message("check my balance")

    # Assert
    assert "1234.56" in response


@pytest.mark.asyncio
async def test_action_registry_unknown_raises():
    """Registry raises error for unknown action."""
    # Arrange
    registry = ActionRegistry()

    # Act & Assert
    with pytest.raises(ValueError, match="Unknown action"):
        await registry.execute("nonexistent", {})


@pytest.mark.asyncio
async def test_action_registry_contains():
    """Registry contains check works."""
    # Arrange
    async def handler(slots):
        return {}

    registry = ActionRegistry()
    registry.register("my_action", handler)

    # Assert
    assert "my_action" in registry
    assert "other" not in registry
