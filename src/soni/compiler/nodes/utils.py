"""Utility functions for node factories.

This module provides reusable validation and helper functions
to reduce code duplication across node factory implementations.
"""

from typing import Any, TypeVar

from soni.config.steps import StepConfig
from soni.core.errors import ValidationError

T = TypeVar("T")


def require_field(step: StepConfig, field: str, field_type: Any = None) -> Any:
    """Validate that a required field exists and optionally check its type.

    Args:
        step: The step configuration to validate
        field: Name of the required field
        field_type: Optional type to validate against

    Returns:
        The field value

    Raises:
        ValidationError: If field is missing or has wrong type
    """
    value = getattr(step, field, None)

    if value is None:
        raise ValidationError(
            f"Step '{step.step}' of type '{step.type}' is missing required field '{field}'"
        )

    if field_type is not None and not isinstance(value, field_type):
        raise ValidationError(
            f"Step '{step.step}' field '{field}' must be {field_type.__name__}, "
            f"got {type(value).__name__}"
        )

    return value


def require_fields(step: StepConfig, *fields: str) -> dict[str, Any]:
    """Validate multiple required fields at once.

    Args:
        step: The step configuration to validate
        *fields: Names of required fields

    Returns:
        Dictionary mapping field names to values

    Raises:
        ValidationError: If any field is missing (reports all missing fields)
    """
    missing: list[str] = []
    values: dict[str, Any] = {}

    for field in fields:
        value = getattr(step, field, None)
        if value is None:
            missing.append(field)
        else:
            values[field] = value

    if missing:
        raise ValidationError(
            f"Step '{step.step}' of type '{step.type}' is missing required fields: "
            f"{', '.join(repr(f) for f in missing)}"
        )

    return values


def validate_non_empty(step: StepConfig, field: str, value: Any) -> None:
    """Validate that a field value is not empty (for lists, dicts, strings).

    Args:
        step: The step configuration (for error context)
        field: Name of the field being validated
        value: The value to check

    Raises:
        ValidationError: If value is empty
    """
    if not value:
        raise ValidationError(f"Step '{step.step}' field '{field}' cannot be empty")


def get_optional_field(step: StepConfig, field: str, default: T | None = None) -> T | Any:
    """Get an optional field with a default value.

    Args:
        step: The step configuration
        field: Name of the optional field
        default: Default value if field is missing

    Returns:
        The field value or default
    """
    value = getattr(step, field, None)
    return value if value is not None else default
