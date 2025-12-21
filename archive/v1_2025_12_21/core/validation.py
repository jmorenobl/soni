"""Core validation logic for Soni.

Provides runtime type checking and coercion for slot values based on config.
"""

from typing import Any

from soni.core.constants import SlotType

from soni.config import SlotConfig


def validate_slot_value(value: Any, config: SlotConfig) -> Any:
    """Validate and coerce a slot value based on configuration.

    Args:
        value: The value to validate.
        config: The slot configuration.

    Returns:
        The validated (and possibly coerced) value.

    Raises:
        ValueError: If the value is invalid for the specified type.
    """
    if value is None:
        return None

    slot_type = config.type

    # STRING
    if slot_type == SlotType.STRING:
        if not isinstance(value, str):
            return str(value)
        return value

    # NUMBER
    if slot_type == SlotType.NUMBER:
        if isinstance(value, (int, float)):
            return value
        if isinstance(value, str):
            try:
                # Try integer first
                if "." not in value:
                    return int(value)
                return float(value)
            except ValueError as e:
                raise ValueError(f"Value '{value}' is not a valid number") from e
        raise ValueError(f"Value '{value}' of type {type(value)} is not a valid number")

    # BOOLEAN
    if slot_type == SlotType.BOOLEAN:
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            lower = value.lower()
            if lower in ("true", "yes", "1", "on"):
                return True
            if lower in ("false", "no", "0", "off"):
                return False
        raise ValueError(f"Value '{value}' cannot be coerced to boolean")

    # LIST
    if slot_type == SlotType.LIST:
        if isinstance(value, list):
            return value
        if isinstance(value, tuple):
            return list(value)
        # Single value to list?
        return [value]

    # DICT
    if slot_type == SlotType.DICT:
        if isinstance(value, dict):
            return value
        raise ValueError(f"Value '{value}' of type {type(value)} is not a valid dict")

    # ANY
    return value
