"""Tests for core validation logic."""

import pytest

from soni.core.config import SlotConfig
from soni.core.constants import SlotType
from soni.core.validation import validate_slot_value


class TestValidator:
    """Test validation logic."""

    def test_validate_string(self):
        """Test string validation."""
        cfg = SlotConfig(type=SlotType.STRING)
        assert validate_slot_value("hello", cfg) == "hello"
        assert validate_slot_value(123, cfg) == "123"

    def test_validate_number(self):
        """Test number validation."""
        cfg = SlotConfig(type=SlotType.NUMBER)
        assert validate_slot_value(123, cfg) == 123
        assert validate_slot_value(12.34, cfg) == 12.34
        assert validate_slot_value("123", cfg) == 123
        assert validate_slot_value("12.34", cfg) == 12.34

        with pytest.raises(ValueError):
            validate_slot_value("abc", cfg)

    def test_validate_boolean(self):
        """Test boolean validation."""
        cfg = SlotConfig(type=SlotType.BOOLEAN)
        assert validate_slot_value(True, cfg) is True
        assert validate_slot_value("true", cfg) is True
        assert validate_slot_value("yes", cfg) is True
        assert validate_slot_value("0", cfg) is False

        with pytest.raises(ValueError):
            validate_slot_value("maybe", cfg)

    def test_validate_list(self):
        """Test list validation."""
        cfg = SlotConfig(type=SlotType.LIST)
        assert validate_slot_value(["a", "b"], cfg) == ["a", "b"]
        assert validate_slot_value("a", cfg) == ["a"]
