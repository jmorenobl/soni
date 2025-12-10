"""Metadata management utilities for dialogue state.

This module provides centralized metadata manipulation following DRY principle.
All metadata flag clearing/setting should go through MetadataManager to avoid
code duplication and ensure consistency.
"""

from typing import Any


class MetadataManager:
    """Centralized metadata manipulation following DRY principle.

    This class encapsulates all metadata flag operations to avoid duplicating
    the same clearing/setting logic across multiple nodes.

    All methods follow immutable pattern: they return NEW metadata dict,
    never modify in place.
    """

    @staticmethod
    def clear_confirmation_flags(metadata: dict[str, Any]) -> dict[str, Any]:
        """Clear confirmation-related flags from metadata.

        Removes all flags related to confirmation flow:
        - _confirmation_attempts: retry counter
        - _confirmation_processed: processing status flag
        - _confirmation_unclear: unclear response flag

        Args:
            metadata: Current metadata dictionary

        Returns:
            New metadata dict with confirmation flags removed
        """
        updated = metadata.copy()
        updated.pop("_confirmation_attempts", None)
        updated.pop("_confirmation_processed", None)
        updated.pop("_confirmation_unclear", None)
        return updated

    @staticmethod
    def clear_correction_flags(metadata: dict[str, Any]) -> dict[str, Any]:
        """Clear correction-related flags from metadata.

        Removes all flags related to slot correction:
        - _correction_slot: name of corrected slot
        - _correction_value: new value after correction

        Args:
            metadata: Current metadata dictionary

        Returns:
            New metadata dict with correction flags removed
        """
        updated = metadata.copy()
        updated.pop("_correction_slot", None)
        updated.pop("_correction_value", None)
        return updated

    @staticmethod
    def clear_modification_flags(metadata: dict[str, Any]) -> dict[str, Any]:
        """Clear modification-related flags from metadata.

        Removes all flags related to slot modification:
        - _modification_slot: name of modified slot
        - _modification_value: new value after modification

        Args:
            metadata: Current metadata dictionary

        Returns:
            New metadata dict with modification flags removed
        """
        updated = metadata.copy()
        updated.pop("_modification_slot", None)
        updated.pop("_modification_value", None)
        return updated

    @staticmethod
    def clear_all_flow_flags(metadata: dict[str, Any]) -> dict[str, Any]:
        """Clear all flow-related flags (confirmation, correction, modification).

        Use this when resetting state between flows or on errors.

        Args:
            metadata: Current metadata dictionary

        Returns:
            New metadata dict with all flow flags removed
        """
        updated = metadata.copy()
        # Confirmation flags
        updated.pop("_confirmation_attempts", None)
        updated.pop("_confirmation_processed", None)
        updated.pop("_confirmation_unclear", None)
        # Correction flags
        updated.pop("_correction_slot", None)
        updated.pop("_correction_value", None)
        # Modification flags
        updated.pop("_modification_slot", None)
        updated.pop("_modification_value", None)
        return updated

    @staticmethod
    def set_correction_flags(
        metadata: dict[str, Any],
        slot_name: str,
        value: Any,
    ) -> dict[str, Any]:
        """Set correction flags and clear modification flags.

        When a correction occurs, we:
        1. Set correction_slot and correction_value
        2. Clear any existing modification flags (mutually exclusive)

        Args:
            metadata: Current metadata dictionary
            slot_name: Name of the corrected slot
            value: New value after correction

        Returns:
            New metadata dict with correction flags set
        """
        updated = metadata.copy()
        updated["_correction_slot"] = slot_name
        updated["_correction_value"] = value
        # Clear modification flags (mutually exclusive)
        updated.pop("_modification_slot", None)
        updated.pop("_modification_value", None)
        return updated

    @staticmethod
    def set_modification_flags(
        metadata: dict[str, Any],
        slot_name: str,
        value: Any,
    ) -> dict[str, Any]:
        """Set modification flags and clear correction flags.

        When a modification occurs, we:
        1. Set modification_slot and modification_value
        2. Clear any existing correction flags (mutually exclusive)

        Args:
            metadata: Current metadata dictionary
            slot_name: Name of the modified slot
            value: New value after modification

        Returns:
            New metadata dict with modification flags set
        """
        updated = metadata.copy()
        updated["_modification_slot"] = slot_name
        updated["_modification_value"] = value
        # Clear correction flags (mutually exclusive)
        updated.pop("_correction_slot", None)
        updated.pop("_correction_value", None)
        return updated

    @staticmethod
    def increment_confirmation_attempts(metadata: dict[str, Any]) -> dict[str, Any]:
        """Increment confirmation retry counter.

        Args:
            metadata: Current metadata dictionary

        Returns:
            New metadata dict with incremented confirmation attempts
        """
        updated = metadata.copy()
        current_attempts = metadata.get("_confirmation_attempts", 0)
        updated["_confirmation_attempts"] = current_attempts + 1
        return updated

    @staticmethod
    def get_confirmation_attempts(metadata: dict[str, Any]) -> int:
        """Get current confirmation retry count.

        Args:
            metadata: Current metadata dictionary

        Returns:
            Number of confirmation attempts (0 if not set)
        """
        attempts = metadata.get("_confirmation_attempts", 0)
        return int(attempts) if isinstance(attempts, (int, str)) else 0
