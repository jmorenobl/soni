"""Slot validation system (M5).

Provides a registry for validator functions and utilities for validating slot values.
Validators can be sync or async, and receive the value + all current slots.

Usage:
    from soni.core.validation import register_validator, validate

    def validate_positive(value: Any, slots: dict) -> bool:
        return float(value) > 0

    register_validator("positive", validate_positive)

    # In collect_node:
    is_valid = await validate(user_value, "positive", slots)
"""

import asyncio
from collections.abc import Awaitable, Callable
from typing import Any

# Type for validator functions: sync or async, receives value and all slots
ValidatorFn = Callable[[Any, dict[str, Any]], bool | Awaitable[bool]]

# Global registry of validators
_validators: dict[str, ValidatorFn] = {}


def register_validator(name: str, fn: ValidatorFn) -> None:
    """Register a validator function.

    Args:
        name: Unique validator name referenced in YAML
        fn: Function that returns True if value is valid
    """
    _validators[name] = fn


def get_validator(name: str) -> ValidatorFn | None:
    """Get a validator by name."""
    return _validators.get(name)


async def validate(value: Any, validator_name: str, slots: dict[str, Any]) -> bool:
    """Run validator on value.

    Args:
        value: The value to validate
        validator_name: Name of registered validator
        slots: All current slot values (for cross-field validation)

    Returns:
        True if valid, False otherwise
    """
    validator = _validators.get(validator_name)
    if not validator:
        # No validator = always valid
        return True

    result = validator(value, slots)

    # Handle async validators
    if asyncio.iscoroutine(result):
        coro_result = await result
        return bool(coro_result)

    return bool(result)


def clear_validators() -> None:
    """Clear all validators (for testing)."""
    _validators.clear()


# Built-in validators
def _validate_not_empty(value: Any, slots: dict[str, Any]) -> bool:
    """Validate value is not empty."""
    if value is None:
        return False
    if isinstance(value, str):
        return bool(value.strip())
    return True


def _validate_positive(value: Any, slots: dict[str, Any]) -> bool:
    """Validate numeric value is positive."""
    try:
        return float(value) > 0
    except (ValueError, TypeError):
        return False


def _validate_email(value: Any, slots: dict[str, Any]) -> bool:
    """Basic email validation."""
    if not isinstance(value, str):
        return False
    return "@" in value and "." in value


# Register built-in validators
register_validator("not_empty", _validate_not_empty)
register_validator("positive", _validate_positive)
register_validator("email", _validate_email)
