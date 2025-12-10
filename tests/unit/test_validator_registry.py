"""Tests for ValidatorRegistry"""

import pytest

from soni.validation.registry import ValidatorRegistry


def test_register_and_get_validator():
    """Test registering and retrieving validator"""

    # Arrange
    @ValidatorRegistry.register("test_validator")
    def test_func(value: str) -> bool:
        return len(value) > 5

    # Act
    validator = ValidatorRegistry.get("test_validator")

    # Assert
    assert validator is test_func
    assert validator("hello world")
    assert not validator("hi")


def test_validate_method():
    """Test validate helper method"""

    # Arrange
    @ValidatorRegistry.register("length_check")
    def check_length(value: str) -> bool:
        return len(value) == 3

    # Act & Assert
    assert ValidatorRegistry.validate("length_check", "abc")
    assert not ValidatorRegistry.validate("length_check", "abcd")


def test_city_name_validator():
    """Test city_name validator"""
    # Act & Assert
    assert ValidatorRegistry.validate("city_name", "Paris")
    assert ValidatorRegistry.validate("city_name", "New York")
    assert ValidatorRegistry.validate("city_name", "San Francisco")
    assert not ValidatorRegistry.validate("city_name", "Paris123")
    assert not ValidatorRegistry.validate("city_name", "P")
    assert not ValidatorRegistry.validate("city_name", "123")


def test_future_date_validator():
    """Test future_date_only validator"""
    from datetime import datetime, timedelta

    # Act & Assert
    future_date = (datetime.now() + timedelta(days=1)).isoformat()
    past_date = (datetime.now() - timedelta(days=1)).isoformat()
    assert ValidatorRegistry.validate("future_date_only", future_date)
    assert not ValidatorRegistry.validate("future_date_only", past_date)
    assert not ValidatorRegistry.validate("future_date_only", "invalid-date")


def test_iata_code_validator():
    """Test iata_code validator"""
    # Act & Assert
    assert ValidatorRegistry.validate("iata_code", "JFK")
    assert ValidatorRegistry.validate("iata_code", "LAX")
    assert not ValidatorRegistry.validate("iata_code", "jkf")  # lowercase
    assert not ValidatorRegistry.validate("iata_code", "JK")  # too short
    assert not ValidatorRegistry.validate("iata_code", "JFK1")  # has number


def test_get_nonexistent_validator():
    """Test getting non-existent validator raises error"""
    # Act & Assert
    with pytest.raises(ValueError, match="not registered"):
        ValidatorRegistry.get("nonexistent_validator")


def test_list_validators():
    """Test listing all validators"""
    # Act
    validators = ValidatorRegistry.list_validators()

    # Assert
    assert isinstance(validators, list)
    assert "city_name" in validators
    assert "future_date_only" in validators
    assert "iata_code" in validators
    # booking_reference should NOT be in framework (moved to examples/)


def test_no_domain_specific_validators_in_registry():
    """Test that framework validator registry contains NO domain-specific validators."""
    # Arrange
    registry_validators = ValidatorRegistry.list_validators()

    # Assert - Framework should only have GENERIC validators
    domain_specific_keywords = [
        "booking",
        "flight",
        "hotel",
        "restaurant",
        "reservation",
        "passenger",
        "table",
    ]

    for validator_name in registry_validators:
        for keyword in domain_specific_keywords:
            assert keyword not in validator_name.lower(), (
                f"Domain-specific validator '{validator_name}' found in framework registry! "
                f"Move to application code (examples/)."
            )


def test_framework_validators_are_generic():
    """Test that all framework validators are truly generic."""
    # Arrange
    expected_generic_validators = [
        "city_name",  # Generic: any city name
        "future_date_only",  # Generic: any future date
        "iata_code",  # Generic: any 3-letter code (not just airports!)
    ]

    # Act
    registry_validators = ValidatorRegistry.list_validators()

    # Assert
    for validator_name in expected_generic_validators:
        assert validator_name in registry_validators, (
            f"Expected generic validator '{validator_name}' not found in registry"
        )
