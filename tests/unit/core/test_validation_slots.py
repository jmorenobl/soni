import asyncio

import pytest

from soni.core.validation import clear_validators, register_validator, validate


class TestSlotValidation:
    """Tests for slot validation system."""

    def setup_method(self):
        """Setup before each test. We don't clear globally to preserve built-ins."""
        pass

    @pytest.mark.asyncio
    async def test_built_in_not_empty(self):
        """Should validate not_empty built-in validator."""
        assert await validate("hello", "not_empty", {}) is True
        assert await validate("  ", "not_empty", {}) is False
        assert await validate(None, "not_empty", {}) is False

    @pytest.mark.asyncio
    async def test_built_in_positive(self):
        """Should validate positive built-in validator."""
        assert await validate(10, "positive", {}) is True
        assert await validate(0, "positive", {}) is False
        assert await validate(-5, "positive", {}) is False
        assert await validate("not a number", "positive", {}) is False

    @pytest.mark.asyncio
    async def test_built_in_email(self):
        """Should validate email built-in validator."""
        assert await validate("test@example.com", "email", {}) is True
        assert await validate("invalid-email", "email", {}) is False
        assert await validate(123, "email", {}) is False

    @pytest.mark.asyncio
    async def test_async_validator(self):
        """Should handle async validator functions."""

        async def async_val(v, s):
            await asyncio.sleep(0)
            return v == "async"

        register_validator("is_async", async_val)
        assert await validate("async", "is_async", {}) is True
        assert await validate("sync", "is_async", {}) is False

    def test_get_validator(self):
        """Should retrieve registered validator."""
        from soni.core.validation import get_validator

        assert get_validator("positive") is not None
        assert get_validator("non_existent") is None
