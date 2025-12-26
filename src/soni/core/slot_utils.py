"""Utilities for slot manipulation.

This module provides the single source of truth for slot-related operations.
"""

from copy import deepcopy
from typing import Any


def deep_merge_flow_slots(
    base: dict[str, dict[str, Any]],
    new: dict[str, dict[str, Any]],
    *,
    in_place: bool = False,
) -> dict[str, dict[str, Any]]:
    """Merge flow slot dictionaries with deep merge for nested values.

    This is the **single source of truth** for flow_slots merging.
    All other merge implementations should delegate to this function.

    Args:
        base: Base flow_slots dictionary {flow_id: {slot_name: value}}
        new: New values to merge into base
        in_place: If True, mutates base. If False, returns new dict.

    Returns:
        Merged dictionary with new values overriding base values.
        For matching flow_ids, slot values are merged (not replaced).

    Example:
        >>> base = {"flow1": {"slot_a": 1, "slot_b": 2}}
        >>> new = {"flow1": {"slot_b": 3, "slot_c": 4}, "flow2": {"slot_x": 5}}
        >>> deep_merge_flow_slots(base, new)
        {
            "flow1": {"slot_a": 1, "slot_b": 3, "slot_c": 4},
            "flow2": {"slot_x": 5}
        }

    Notes:
        - New flow_ids are added to the result
        - For existing flow_ids, slots are merged (not replaced)
        - Individual slot values are replaced (not deep merged)
        - None values in new dict DO overwrite base values
    """
    if not new:
        return base if in_place else dict(base)

    result = base if in_place else deepcopy(base)

    for flow_id, slots in new.items():
        if flow_id in result:
            # Merge slots for existing flow
            result[flow_id] = {**result[flow_id], **slots}
        else:
            # Add new flow
            result[flow_id] = dict(slots)

    return result


def get_slot_value(
    flow_slots: dict[str, dict[str, Any]],
    flow_id: str,
    slot_name: str,
    default: Any = None,
) -> Any:
    """Get a slot value safely with default.

    Args:
        flow_slots: Flow slots dictionary
        flow_id: Flow instance ID
        slot_name: Name of the slot
        default: Value to return if not found

    Returns:
        Slot value or default
    """
    return flow_slots.get(flow_id, {}).get(slot_name, default)


def set_slot_value(
    flow_slots: dict[str, dict[str, Any]],
    flow_id: str,
    slot_name: str,
    value: Any,
) -> dict[str, dict[str, Any]]:
    """Set a slot value immutably.

    Args:
        flow_slots: Flow slots dictionary
        flow_id: Flow instance ID
        slot_name: Name of the slot
        value: Value to set

    Returns:
        New flow_slots dict with updated value
    """
    result = deepcopy(flow_slots)
    if flow_id not in result:
        result[flow_id] = {}
    result[flow_id][slot_name] = value
    return result
