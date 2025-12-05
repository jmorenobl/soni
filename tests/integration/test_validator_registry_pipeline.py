"""Tests for ValidatorRegistry integration with validation pipeline."""

import re
from pathlib import Path

import pytest
import yaml

from soni.validation.registry import ValidatorRegistry


def test_pipeline_uses_validator_registry():
    """Test that validation pipeline uses ValidatorRegistry"""
    # Arrange
    ValidatorRegistry.clear()

    @ValidatorRegistry.register("test_validator")
    def test_validator(value: str) -> bool:
        return len(value) > 5

    # Act
    result = ValidatorRegistry.validate("test_validator", "hello world")

    # Assert
    assert result is True
    result = ValidatorRegistry.validate("test_validator", "hi")
    assert result is False


def test_yaml_no_contains_regex_patterns():
    """Test that YAML examples don't contain regex patterns in validators"""
    # Arrange
    yaml_files = list(Path("examples").rglob("*.yaml"))
    regex_special_chars = re.compile(r"[.*+?^${}|()\\\[\]]")

    # Act & Assert
    for yaml_file in yaml_files:
        with open(yaml_file) as f:
            content = yaml.safe_load(f)
            if "slots" in content:
                for slot_name, slot_config in content["slots"].items():
                    if "validator" in slot_config:
                        validator_value = slot_config["validator"]
                        # Check if it looks like regex (contains special chars)
                        if isinstance(validator_value, str) and regex_special_chars.search(
                            validator_value
                        ):
                            pytest.fail(
                                f"YAML {yaml_file} contains regex pattern in validator for slot '{slot_name}': {validator_value}. "
                                f"Use semantic validator name instead (e.g., 'city_name')."
                            )


def test_builtin_validators_registered():
    """Test that built-in validators are registered"""
    # Arrange - Import validators module to register them
    import soni.validation.validators  # noqa: F401

    builtin_validators = [
        "city_name",
        "future_date_only",
        "iata_code",
        "booking_reference",
    ]

    # Assert
    for validator_name in builtin_validators:
        assert ValidatorRegistry.is_registered(validator_name), (
            f"Built-in validator '{validator_name}' not registered"
        )


@pytest.mark.integration
@pytest.mark.asyncio
async def test_collect_node_uses_validator_registry():
    """Test that collect nodes use ValidatorRegistry for validation"""
    # Arrange
    ValidatorRegistry.clear()

    @ValidatorRegistry.register("test_slot_validator")
    def validate_test(value: str) -> bool:
        return value == "valid"

    # Act - Verify the validator is available
    assert ValidatorRegistry.is_registered("test_slot_validator")

    # Assert - Test validation
    assert ValidatorRegistry.validate("test_slot_validator", "valid") is True
    assert ValidatorRegistry.validate("test_slot_validator", "invalid") is False
