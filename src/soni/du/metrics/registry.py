"""Extensible registry for command type field definitions."""


class FieldRegistry:
    """Extensible registry for command type field definitions.

    Allows new command types to be registered with their key and value fields
    for metric scoring purposes.
    """

    _key_fields: dict[str, list[str]] = {}
    _value_fields: dict[str, list[str]] = {}

    @classmethod
    def register_command_type(
        cls,
        cmd_type: str,
        key_fields: list[str] | None = None,
        value_fields: list[str] | None = None,
    ) -> None:
        """Register field definitions for a command type.

        Args:
            cmd_type: Command type name (e.g., "start_flow", "set_slot")
            key_fields: Fields that must match exactly for correctness
            value_fields: Fields that are compared with fuzzy matching
        """
        cls._key_fields[cmd_type] = key_fields or []
        cls._value_fields[cmd_type] = value_fields or []

    @classmethod
    def get_key_fields(cls, cmd_type: str) -> list[str]:
        """Get key fields for a command type."""
        return cls._key_fields.get(cmd_type, [])

    @classmethod
    def get_value_fields(cls, cmd_type: str) -> list[str]:
        """Get value fields for a command type."""
        return cls._value_fields.get(cmd_type, [])

    @classmethod
    def list_registered_types(cls) -> list[str]:
        """List all registered command types."""
        return sorted(set(cls._key_fields.keys()) | set(cls._value_fields.keys()))


# Register default command types
FieldRegistry.register_command_type("start_flow", key_fields=["flow_name"], value_fields=["slots"])
FieldRegistry.register_command_type("set_slot", key_fields=["slot"], value_fields=["value"])
FieldRegistry.register_command_type("correct_slot", key_fields=["slot"], value_fields=["new_value"])
FieldRegistry.register_command_type("cancel_flow", key_fields=[], value_fields=["reason"])
FieldRegistry.register_command_type("affirm", key_fields=[], value_fields=[])
FieldRegistry.register_command_type("deny", key_fields=["slot_to_change"], value_fields=[])
FieldRegistry.register_command_type("clarify", key_fields=[], value_fields=["topic"])
FieldRegistry.register_command_type("chitchat", key_fields=[], value_fields=["message"])

# Backwards compatibility aliases
KEY_FIELDS = FieldRegistry._key_fields
VALUE_FIELDS = FieldRegistry._value_fields
