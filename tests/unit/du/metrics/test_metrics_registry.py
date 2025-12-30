import pytest

from soni.du.metrics.registry import FieldRegistry


class TestFieldRegistry:
    """Tests for FieldRegistry."""

    def test_registration_and_retrieval(self):
        """Should register and retrieve field definitions."""
        FieldRegistry.register_command_type("custom_cmd", key_fields=["k1"], value_fields=["v1"])

        assert FieldRegistry.get_key_fields("custom_cmd") == ["k1"]
        assert FieldRegistry.get_value_fields("custom_cmd") == ["v1"]

        # Missing type
        assert FieldRegistry.get_key_fields("non_existent") == []

    def test_list_registered_types(self):
        """Should list all registered types."""
        types = FieldRegistry.list_registered_types()
        assert "start_flow" in types
        assert "custom_cmd" in types
        assert isinstance(types, list)
