"""Tests for server error handling - ensures no sensitive data exposure."""

import pytest
from soni.core.errors import (
    ConfigError,
    FlowError,
    NLUError,
    ValidationError,
)

from soni.server.errors import (
    create_error_reference,
    create_error_response,
    get_http_status_for_exception,
    get_safe_error_message,
)


class TestErrorReferenceGeneration:
    """Test error reference creation."""

    def test_creates_unique_references(self):
        """Each call should produce unique reference."""
        refs = {create_error_reference() for _ in range(100)}
        assert len(refs) == 100  # All unique

    def test_reference_format(self):
        """Reference should follow ERR-XXXXXXXX format."""
        ref = create_error_reference()
        assert ref.startswith("ERR-")
        assert len(ref) == 12  # ERR- + 8 hex chars


class TestSafeErrorMessages:
    """Test error message sanitization."""

    def test_config_error_message_is_generic(self):
        """ConfigError should not expose details."""
        exc = ConfigError("secret/path/to/config.yaml not found")
        msg = get_safe_error_message(exc)
        assert "secret" not in msg.lower()
        assert "path" not in msg.lower()
        assert "configuration" in msg.lower()

    def test_validation_error_message_is_generic(self):
        """ValidationError should not expose field details."""
        exc = ValidationError("Field 'password' invalid: must be 8 chars")
        msg = get_safe_error_message(exc)
        assert "password" not in msg.lower()
        assert "invalid" in msg.lower()

    def test_unknown_exception_gets_default_message(self):
        """Unknown exceptions should get generic message."""
        exc = RuntimeError("Internal database connection string: postgres://...")
        msg = get_safe_error_message(exc)
        assert "postgres" not in msg.lower()
        assert "database" not in msg.lower()
        assert "internal" in msg.lower()

    def test_no_stack_trace_in_message(self):
        """Error messages should never contain stack traces."""
        try:
            raise ValueError("test error")
        except ValueError as e:
            msg = get_safe_error_message(e)
            assert "Traceback" not in msg
            assert "File" not in msg
            assert "line" not in msg


class TestHttpStatusMapping:
    """Test exception to HTTP status code mapping."""

    def test_validation_error_returns_400(self):
        """ValidationError should be client error."""
        assert get_http_status_for_exception(ValidationError("x")) == 400

    def test_nlu_error_returns_422(self):
        """NLUError should be unprocessable entity."""
        assert get_http_status_for_exception(NLUError("x")) == 422

    def test_config_error_returns_500(self):
        """ConfigError should be server error."""
        assert get_http_status_for_exception(ConfigError("x")) == 500

    def test_flow_error_returns_500(self):
        """FlowError should be server error."""
        assert get_http_status_for_exception(FlowError("x")) == 500

    def test_unknown_error_returns_500(self):
        """Unknown errors default to 500."""
        assert get_http_status_for_exception(RuntimeError("x")) == 500


class TestCreateErrorResponse:
    """Test HTTPException creation."""

    def test_response_contains_reference(self):
        """Response should include error reference."""
        exc = ValueError("secret info")
        response = create_error_response(exc)
        assert isinstance(response.detail, dict)
        assert "reference" in response.detail
        assert response.detail["reference"].startswith("ERR-")

    def test_response_does_not_contain_original_message(self):
        """Original exception message should not be in response."""
        exc = ValueError("database password is xyz123")
        response = create_error_response(exc)
        assert "xyz123" not in str(response.detail)
        assert "password" not in str(response.detail).lower()

    def test_response_has_correct_status_for_validation(self):
        """Status code should match exception type."""
        exc = ValidationError("x")
        response = create_error_response(exc)
        assert response.status_code == 400

    def test_response_has_correct_status_for_config(self):
        """Config errors should return 500."""
        exc = ConfigError("x")
        response = create_error_response(exc)
        assert response.status_code == 500


class TestNoSensitiveDataExposure:
    """Integration tests verifying no data exposure."""

    @pytest.mark.parametrize(
        "sensitive_data",
        [
            "/Users/jorge/secret/path",
            "postgres://user:password@localhost/db",
            "api_key=sk-1234567890abcdef",
            "Traceback (most recent call last):",
            'File "/home/user/app/main.py", line 42',
            "OPENAI_API_KEY=sk-test",
        ],
    )
    def test_sensitive_data_not_in_response(self, sensitive_data: str):
        """Verify various sensitive data types are not exposed."""
        exc = RuntimeError(f"Error with {sensitive_data}")
        response = create_error_response(exc)
        response_str = str(response.detail).lower()

        # Check key sensitive patterns
        assert "users/" not in response_str
        assert "postgres://" not in response_str
        assert "api_key" not in response_str
        assert "traceback" not in response_str
        assert 'file "' not in response_str
        assert "sk-" not in response_str
