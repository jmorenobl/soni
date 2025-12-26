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


def validate_slot_definition(slot: dict[str, Any]) -> None:
    """Validate a slot definition dictionary.

    Args:
        slot: Dictionary containing slot definition (name, type, etc.)

    Raises:
        ValidationError: If definition is invalid.
    """
    from soni.core.errors import ValidationError

    if "name" not in slot:
        raise ValidationError("Slot definition missing 'name'")

    valid_types = {"string", "number", "boolean", "object", "array"}
    slot_type = slot.get("type", "string")
    if slot_type not in valid_types:
        raise ValidationError(f"Invalid slot type '{slot_type}'. Valid: {valid_types}")

    if slot_type == "number" and "validation" in slot:
        rules = slot["validation"]
        if "min" in rules and "max" in rules:
            if rules["min"] > rules["max"]:
                raise ValidationError(
                    f"Slot '{slot['name']}': min ({rules['min']}) > max ({rules['max']})"
                )


def validate_flow_definition(flow: dict[str, Any]) -> None:
    """Validate a flow definition dictionary.

    Args:
        flow: Dictionary containing flow definition (name, steps, etc.)

    Raises:
        ValidationError: If definition is invalid.
    """
    from soni.core.errors import ValidationError

    if "name" not in flow:
        raise ValidationError("Flow definition missing 'name'")

    if "steps" not in flow or not flow["steps"]:
        raise ValidationError(f"Flow '{flow['name']}' missing 'steps'")

    steps = flow["steps"]
    step_ids = set()

    valid_types = {"say", "collect", "confirm", "action", "branch", "call", "link", "set", "while"}

    for i, step in enumerate(steps):
        if not isinstance(step, dict):
            raise ValidationError(f"Flow '{flow['name']}', step {i} is not a dictionary")

        step_type = step.get("type")
        if step_type not in valid_types:
            raise ValidationError(f"Flow '{flow['name']}', step {i}: invalid type '{step_type}'")

        step_id = step.get("step") or step.get("id")
        if step_id:
            if step_id in step_ids:
                raise ValidationError(f"Flow '{flow['name']}': duplicate step ID '{step_id}'")
            step_ids.add(step_id)

    # Check references (goto)
    for i, step in enumerate(steps):
        goto = step.get("goto")
        if goto and goto not in step_ids and goto not in ("END", "END_FLOW"):
            # Simple check, some gpt-generated flows might use END or similar
            raise ValidationError(
                f"Flow '{flow['name']}', step {i}: invalid goto reference '{goto}'"
            )
