"""Tests for FlowValidator"""

from pathlib import Path

import pytest

from soni.core.config import SoniConfig
from soni.core.errors import ValidationError
from soni.dm.validators import FlowValidator


def test_flow_validator_validates_existing_flow():
    """Test validator accepts valid flow"""
    # Arrange
    config_path = Path("examples/flight_booking/soni.yaml")
    config = SoniConfig.from_yaml(config_path)
    validator = FlowValidator(config)

    # Act & Assert (no exception)
    validator.validate_flow("book_flight")


def test_flow_validator_raises_on_missing_flow():
    """Test validator raises ValidationError for missing flow"""
    # Arrange
    config_path = Path("examples/flight_booking/soni.yaml")
    config = SoniConfig.from_yaml(config_path)
    validator = FlowValidator(config)

    # Act & Assert
    with pytest.raises(ValidationError) as exc_info:
        validator.validate_flow("nonexistent_flow")

    # Assert error details
    assert "nonexistent_flow" in str(exc_info.value)
    assert exc_info.value.field == "flow_name"
    assert exc_info.value.value == "nonexistent_flow"
    assert "available_flows" in exc_info.value.context


def test_flow_validator_raises_on_missing_slot():
    """Test validator raises ValidationError when flow references non-existent slot"""
    # Arrange
    config_path = Path("examples/flight_booking/soni.yaml")
    config = SoniConfig.from_yaml(config_path)

    # Create a flow with invalid slot reference
    from soni.core.config import FlowConfig, StepConfig

    invalid_flow = FlowConfig(
        description="Test flow with invalid slot",
        steps=[
            StepConfig(
                step="collect_invalid",
                type="collect",
                slot="nonexistent_slot",
            )
        ],
    )

    # Manually add invalid flow to config (for testing)
    config.flows["invalid_flow"] = invalid_flow
    validator = FlowValidator(config)

    # Act & Assert
    with pytest.raises(ValidationError) as exc_info:
        validator.validate_flow("invalid_flow")

    # Assert error details
    assert "nonexistent_slot" in str(exc_info.value)
    assert exc_info.value.field == "slot"
    assert exc_info.value.value == "nonexistent_slot"
    assert "available_slots" in exc_info.value.context


def test_flow_validator_raises_on_missing_action():
    """Test validator raises ValidationError when flow references non-existent action"""
    # Arrange
    config_path = Path("examples/flight_booking/soni.yaml")
    config = SoniConfig.from_yaml(config_path)

    # Create a flow with invalid action reference
    from soni.core.config import FlowConfig, StepConfig

    invalid_flow = FlowConfig(
        description="Test flow with invalid action",
        steps=[
            StepConfig(
                step="action_invalid",
                type="action",
                call="nonexistent_action",
            )
        ],
    )

    # Manually add invalid flow to config (for testing)
    config.flows["invalid_action_flow"] = invalid_flow
    validator = FlowValidator(config)

    # Act & Assert
    with pytest.raises(ValidationError) as exc_info:
        validator.validate_flow("invalid_action_flow")

    # Assert error details
    assert "nonexistent_action" in str(exc_info.value)
    assert exc_info.value.field == "action"
    assert exc_info.value.value == "nonexistent_action"
    assert "available_actions" in exc_info.value.context


def test_flow_validator_validates_valid_flow_with_slots_and_actions():
    """Test validator accepts flow with valid slots and actions"""
    # Arrange
    config_path = Path("examples/flight_booking/soni.yaml")
    config = SoniConfig.from_yaml(config_path)
    validator = FlowValidator(config)

    # Act & Assert (no exception)
    # book_flight flow should have valid slots and actions
    validator.validate_flow("book_flight")
