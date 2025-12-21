import pytest
from soni.core.errors import ValidationError

from soni.config.steps import (
    SayStepConfig,
    SetStepConfig,
)


class TestRequireField:
    """Tests for require_field utility."""

    def test_returns_value_when_field_exists(self):
        """Test that existing field value is returned."""
        from soni.compiler.nodes.utils import require_field

        step = SayStepConfig(step="greet", type="say", message="Hello")

        result = require_field(step, "message")

        assert result == "Hello"

    def test_raises_validation_error_when_field_missing(self):
        """Test that ValidationError is raised for missing field."""
        from soni.compiler.nodes.utils import require_field

        # For this test we need a step missing a field.
        # Pydantic models validate on init, so we might need to bypass validation
        # or use construct/mock if we want to test missing required fields
        # that Pydantic would normally catch.
        # However, require_field is useful for optional fields that become required
        # in certain contexts, or if we are validating raw dicts converted to objects (less likely with Pydantic).

        # Actually, Pydantic WILL prevent creating invalid objects.
        # But 'require_field' logic handles checking 'getattr(..., None)'.
        # To test the utility, we can use a mock object or constructs.

        class MockStep:
            step = "greet"
            type = "say"
            # message is missing

        step = MockStep()

        with pytest.raises(ValidationError) as exc_info:
            require_field(step, "message")  # type: ignore

        assert "missing required field 'message'" in str(exc_info.value)
        assert "greet" in str(exc_info.value)

    def test_validates_type_when_specified(self):
        """Test that type validation works."""
        from soni.compiler.nodes.utils import require_field

        # We need a step where a field exists but has wrong type.
        # Pydantic prevents this usually. We'll use a mock.
        class MockStep:
            step = "check"
            type = "branch"
            cases = ["not", "a", "dict"]  # Wrong type for cases

        step = MockStep()

        with pytest.raises(ValidationError) as exc_info:
            require_field(step, "cases", dict)  # type: ignore

        assert "must be dict" in str(exc_info.value)

    def test_accepts_correct_type(self):
        """Test that correct type passes validation."""
        from soni.compiler.nodes.utils import require_field

        step = SayStepConfig(step="greet", type="say", message="Hello")

        result = require_field(step, "message", str)

        assert result == "Hello"


class TestRequireFields:
    """Tests for require_fields utility."""

    def test_returns_all_values_when_fields_exist(self):
        """Test that all field values are returned."""
        from soni.compiler.nodes.utils import require_fields

        step = SetStepConfig(step="assign", type="set", slots={"name": "John"})

        result = require_fields(step, "slots")

        assert result == {"slots": {"name": "John"}}

    def test_raises_for_first_missing_field(self):
        """Test that ValidationError mentions all missing fields."""
        from soni.compiler.nodes.utils import require_fields

        class MockStep:
            step = "assign"
            type = "set"
            # Missing slots

        step = MockStep()

        with pytest.raises(ValidationError) as exc_info:
            require_fields(step, "slots", "other")  # type: ignore

        error_msg = str(exc_info.value)
        assert "'slots'" in error_msg
        assert "'other'" in error_msg

    def test_partial_missing_fields(self):
        """Test error when only some fields missing."""
        from soni.compiler.nodes.utils import require_fields

        class MockStep:
            step = "assign"
            type = "set"
            slots = {"name": "John"}
            # Missing value

        step = MockStep()

        with pytest.raises(ValidationError) as exc_info:
            require_fields(step, "slots", "value")  # type: ignore

        error_msg = str(exc_info.value)
        assert "'value'" in error_msg
        assert "'slots'" not in error_msg  # slot exists


class TestValidateNonEmpty:
    """Tests for validate_non_empty utility."""

    def test_passes_for_non_empty_string(self):
        """Test that non-empty string passes."""
        from soni.compiler.nodes.utils import validate_non_empty

        step = SayStepConfig(step="test", type="say", message="Hello")

        validate_non_empty(step, "message", "Hello")  # Should not raise

    def test_raises_for_empty_string(self):
        """Test that empty string raises."""
        from soni.compiler.nodes.utils import validate_non_empty

        class MockStep:
            step = "test"
            type = "say"

        step = MockStep()

        with pytest.raises(ValidationError) as exc_info:
            validate_non_empty(step, "message", "")  # type: ignore

        assert "cannot be empty" in str(exc_info.value)

    def test_raises_for_empty_list(self):
        """Test that empty list raises."""
        from soni.compiler.nodes.utils import validate_non_empty

        class MockStep:
            step = "loop"
            type = "while"

        step = MockStep()

        with pytest.raises(ValidationError):
            validate_non_empty(step, "do", [])  # type: ignore


class TestGetOptionalField:
    """Tests for get_optional_field utility."""

    def test_returns_value_when_exists(self):
        """Test that existing value is returned."""
        from soni.compiler.nodes.utils import get_optional_field

        step = SayStepConfig(step="test", type="say", message="Hello")

        result = get_optional_field(step, "message", "Default")

        assert result == "Hello"

    def test_returns_default_when_missing(self):
        """Test that default is returned for missing field."""
        from soni.compiler.nodes.utils import get_optional_field

        step = SayStepConfig(step="test", message="Hello")

        result = get_optional_field(step, "nonexistent", "Default")

        assert result == "Default"

    def test_returns_none_by_default(self):
        """Test that None is default default."""
        from soni.compiler.nodes.utils import get_optional_field

        step = SayStepConfig(step="test", message="Hello")

        result = get_optional_field(step, "nonexistent")

        assert result is None
