import pytest

from soni.core.errors import ValidationError
from soni.core.validation import validate_flow_definition, validate_slot_definition


class TestDefinitionValidation:
    """Tests for slot and flow definition validation."""

    def test_valid_slot_definition(self):
        """Should pass for valid slot definitions."""
        valid_slots = [
            {"name": "test", "type": "string"},
            {"name": "age", "type": "number", "validation": {"min": 0, "max": 100}},
            {"name": "metadata", "type": "object"},
            {"name": "tags", "type": "array"},
        ]
        for slot in valid_slots:
            validate_slot_definition(slot)

    def test_invalid_slot_definition(self):
        """Should raise ValidationError for invalid slot definitions."""
        with pytest.raises(ValidationError, match="missing 'name'"):
            validate_slot_definition({"type": "string"})

        with pytest.raises(ValidationError, match="Invalid slot type"):
            validate_slot_definition({"name": "test", "type": "invalid"})

        with pytest.raises(ValidationError, match="min.*>.*max"):
            validate_slot_definition(
                {"name": "test", "type": "number", "validation": {"min": 100, "max": 0}}
            )

    def test_valid_flow_definition(self):
        """Should pass for valid flow definitions."""
        flow = {
            "name": "test_flow",
            "steps": [
                {"step": "s1", "type": "say", "message": "hello", "goto": "s2"},
                {"step": "s2", "type": "collect", "slot": "s", "message": "m", "goto": "END"},
            ],
        }
        validate_flow_definition(flow)

    def test_invalid_flow_definition(self):
        """Should raise ValidationError for invalid flow definitions."""
        with pytest.raises(ValidationError, match="missing 'name'"):
            validate_flow_definition({"steps": []})

        with pytest.raises(ValidationError, match="missing 'steps'"):
            validate_flow_definition({"name": "test"})

        with pytest.raises(ValidationError, match="missing 'steps'"):
            validate_flow_definition({"name": "test", "steps": []})

        with pytest.raises(ValidationError, match="not a dictionary"):
            validate_flow_definition({"name": "test", "steps": ["not a dict"]})

    def test_invalid_step_types(self):
        """Should reject invalid step types."""
        flow = {"name": "test", "steps": [{"type": "invalid"}]}
        with pytest.raises(ValidationError, match="invalid type"):
            validate_flow_definition(flow)

    def test_duplicate_step_ids(self):
        """Should reject duplicate step IDs."""
        flow = {
            "name": "test",
            "steps": [
                {"step": "s1", "type": "say", "message": "h"},
                {"id": "s1", "type": "say", "message": "duplicate"},
            ],
        }
        with pytest.raises(ValidationError, match="duplicate step ID"):
            validate_flow_definition(flow)

    def test_invalid_goto_reference(self):
        """Should reject invalid goto references."""
        flow = {
            "name": "test",
            "steps": [{"step": "s1", "type": "say", "message": "h", "goto": "non_existent"}],
        }
        with pytest.raises(ValidationError, match="invalid goto reference"):
            validate_flow_definition(flow)
