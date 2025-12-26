import pytest

from soni.core.validation import clear_validators, register_validator, validate


class TestSlotValidation:
    """Tests for slot validation system."""

    def setup_method(self):
        """Setup before each test."""
        clear_validators()
        register_validator("positive", lambda v, s: float(v) > 0)

    @pytest.mark.asyncio
    async def test_valid_value_passes(self):
        """Valid value should pass validation."""
        is_valid = await validate(100, "positive", {})
        assert is_valid is True

    @pytest.mark.asyncio
    async def test_invalid_value_fails(self):
        """Invalid value should fail validation."""
        is_valid = await validate(-100, "positive", {})
        assert is_valid is False

    @pytest.mark.asyncio
    async def test_no_validator_passes(self):
        """Value with non-existent validator should pass (default)."""
        is_valid = await validate("any", "non_existent", {})
        assert is_valid is True
