"""Test NLU result validation (DM-005).

TDD Red Phase: Tests for Pydantic validation at routing boundary.
"""

import pytest

from soni.core.constants import MessageType


class TestValidatedNLUResultModel:
    """Test ValidatedNLUResult Pydantic model."""

    def test_model_exists_and_importable(self):
        """ValidatedNLUResult should be importable from routing module."""
        from soni.dm.routing import ValidatedNLUResult

        assert ValidatedNLUResult is not None

    def test_valid_nlu_result_passes(self):
        """Valid NLU result dict should validate successfully."""
        from soni.dm.routing import ValidatedNLUResult

        data = {
            "message_type": "slot_value",
            "command": None,
            "slots": [],
            "confidence": 0.9,
        }
        result = ValidatedNLUResult.model_validate(data)

        assert result.message_type == "slot_value"
        assert result.confidence == 0.9

    def test_missing_required_field_fails(self):
        """Missing required field should raise ValidationError."""
        from pydantic import ValidationError

        from soni.dm.routing import ValidatedNLUResult

        data = {"slots": []}  # missing message_type

        with pytest.raises(ValidationError):
            ValidatedNLUResult.model_validate(data)


class TestValidateNLUResultFunction:
    """Test validate_nlu_result helper function."""

    def test_function_exists_and_importable(self):
        """validate_nlu_result should be importable."""
        from soni.dm.routing import validate_nlu_result

        assert callable(validate_nlu_result)

    def test_none_input_returns_none(self):
        """None input should return None."""
        from soni.dm.routing import validate_nlu_result

        result = validate_nlu_result(None)
        assert result is None

    def test_valid_dict_returns_model(self):
        """Valid dict should return ValidatedNLUResult."""
        from soni.dm.routing import ValidatedNLUResult, validate_nlu_result

        data = {
            "message_type": "slot_value",
            "slots": [],
            "confidence": 0.85,
        }
        result = validate_nlu_result(data)

        assert isinstance(result, ValidatedNLUResult)
        assert result.message_type == "slot_value"

    def test_invalid_dict_raises_or_returns_none(self):
        """Invalid dict should raise NLUResultValidationError or return fallback."""
        from soni.dm.routing import NLUResultValidationError, validate_nlu_result

        data = {"invalid": "data"}

        with pytest.raises(NLUResultValidationError):
            validate_nlu_result(data)


class TestNLUResultValidationError:
    """Test custom validation error."""

    def test_error_exists_and_importable(self):
        """NLUResultValidationError should be importable."""
        from soni.dm.routing import NLUResultValidationError

        assert NLUResultValidationError is not None

    def test_error_contains_original_data(self):
        """Error should contain the original data that failed validation."""
        from soni.dm.routing import validate_nlu_result

        bad_data = {"invalid": "data"}

        try:
            validate_nlu_result(bad_data)
        except Exception as e:
            assert hasattr(e, "original_data") or "invalid" in str(e)
