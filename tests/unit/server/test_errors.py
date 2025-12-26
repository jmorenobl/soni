"""Tests for server error handling functions."""

import pytest
from fastapi import HTTPException

from soni.core.errors import (
    ActionError,
    ConfigError,
    FlowError,
    NLUError,
    SlotError,
    StateError,
    ValidationError,
)
from soni.server.errors import (
    DEFAULT_ERROR_MESSAGE,
    create_error_reference,
    create_error_response,
    get_http_status_for_exception,
    get_safe_error_message,
)


class TestCreateErrorReference:
    """Tests for create_error_reference function."""

    def test_returns_string(self):
        """Should return a string."""
        ref = create_error_reference()
        assert isinstance(ref, str)

    def test_starts_with_err(self):
        """Reference should start with ERR-."""
        ref = create_error_reference()
        assert ref.startswith("ERR-")

    def test_unique_references(self):
        """Each call should return unique reference."""
        refs = [create_error_reference() for _ in range(10)]
        assert len(set(refs)) == 10


class TestGetSafeErrorMessage:
    """Tests for get_safe_error_message function."""

    def test_config_error(self):
        """ConfigError should return safe message."""
        msg = get_safe_error_message(ConfigError("secret path"))
        assert "secret" not in msg
        assert "Configuration error" in msg

    def test_validation_error(self):
        """ValidationError should return safe message."""
        msg = get_safe_error_message(ValidationError("invalid data"))
        assert "Invalid request data" in msg

    def test_flow_error(self):
        """FlowError should return safe message."""
        msg = get_safe_error_message(FlowError("internal flow details"))
        assert "Flow execution error" in msg

    def test_nlu_error(self):
        """NLUError should return safe message."""
        msg = get_safe_error_message(NLUError("model failure"))
        assert "Unable to understand" in msg

    def test_state_error(self):
        """StateError should return safe message."""
        msg = get_safe_error_message(StateError("session corruption"))
        assert "Session state error" in msg

    def test_unknown_error_returns_default(self):
        """Unknown error should return default message."""
        msg = get_safe_error_message(RuntimeError("unknown"))
        assert msg == DEFAULT_ERROR_MESSAGE


class TestGetHttpStatusForException:
    """Tests for get_http_status_for_exception function."""

    def test_validation_error_400(self):
        """ValidationError should return 400."""
        status = get_http_status_for_exception(ValidationError("bad"))
        assert status == 400

    def test_slot_error_422(self):
        """SlotError should return 422."""
        status = get_http_status_for_exception(SlotError("invalid slot"))
        assert status == 422

    def test_nlu_error_422(self):
        """NLUError should return 422."""
        status = get_http_status_for_exception(NLUError("parse fail"))
        assert status == 422

    def test_config_error_500(self):
        """ConfigError should return 500."""
        status = get_http_status_for_exception(ConfigError("bad config"))
        assert status == 500

    def test_flow_error_500(self):
        """FlowError should return 500."""
        status = get_http_status_for_exception(FlowError("flow crash"))
        assert status == 500

    def test_action_error_500(self):
        """ActionError should return 500."""
        status = get_http_status_for_exception(ActionError("action fail"))
        assert status == 500

    def test_state_error_500(self):
        """StateError should return 500."""
        status = get_http_status_for_exception(StateError("state fail"))
        assert status == 500

    def test_unknown_error_500(self):
        """Unknown error should return 500."""
        status = get_http_status_for_exception(RuntimeError("unknown"))
        assert status == 500


class TestCreateErrorResponse:
    """Tests for create_error_response function."""

    def test_returns_http_exception(self):
        """Should return HTTPException."""
        error = ConfigError("test")
        response = create_error_response(error)
        assert isinstance(response, HTTPException)

    def test_contains_reference(self):
        """Response should contain error reference."""
        error = FlowError("test")
        response = create_error_response(error)
        assert "reference" in response.detail
        assert response.detail["reference"].startswith("ERR-")

    def test_contains_safe_message(self):
        """Response should contain safe error message."""
        error = NLUError("internal details")
        response = create_error_response(error)
        assert "error" in response.detail
        assert "internal" not in response.detail["error"]

    def test_correct_status_code(self):
        """Response should have correct status code."""
        error = ValidationError("bad input")
        response = create_error_response(error)
        assert response.status_code == 400
