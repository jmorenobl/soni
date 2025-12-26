"""Tests for server Pydantic models."""

import pytest
from pydantic import ValidationError

from soni.server.models import (
    ComponentStatus,
    HealthResponse,
    MessageRequest,
    MessageResponse,
    ReadinessResponse,
    ResetResponse,
    StateResponse,
    VersionResponse,
)


class TestMessageRequest:
    """Tests for MessageRequest model."""

    def test_valid_request(self):
        """Valid request should be accepted."""
        request = MessageRequest(message="Hello", user_id="test-123")
        assert request.message == "Hello"
        assert request.user_id == "test-123"

    def test_empty_message_fails(self):
        """Empty message should fail validation."""
        with pytest.raises(ValidationError):
            MessageRequest(message="", user_id="test")

    def test_missing_user_id_fails(self):
        """Missing user_id should fail validation."""
        with pytest.raises(ValidationError):
            MessageRequest(message="Hello")

    def test_missing_message_fails(self):
        """Missing message should fail validation."""
        with pytest.raises(ValidationError):
            MessageRequest(user_id="test")


class TestMessageResponse:
    """Tests for MessageResponse model."""

    def test_valid_response(self):
        """Valid response should be created."""
        response = MessageResponse(response="Hello!")
        assert response.response == "Hello!"
        assert response.flow_state == "idle"  # default

    def test_with_all_fields(self):
        """Response with all fields should work."""
        response = MessageResponse(
            response="Hello!",
            flow_state="active",
            active_flow="transfer",
            turn_count=5,
        )
        assert response.flow_state == "active"
        assert response.active_flow == "transfer"
        assert response.turn_count == 5


class TestComponentStatus:
    """Tests for ComponentStatus model."""

    def test_valid_status(self):
        """Valid component status should be created."""
        status = ComponentStatus(name="runtime", status="healthy")
        assert status.name == "runtime"
        assert status.status == "healthy"

    def test_with_message(self):
        """Status with message should work."""
        status = ComponentStatus(name="db", status="degraded", message="High latency")
        assert status.message == "High latency"


class TestHealthResponse:
    """Tests for HealthResponse model."""

    def test_valid_response(self):
        """Valid health response should be created."""
        response = HealthResponse(status="healthy", version="1.0.0")
        assert response.status == "healthy"
        assert response.version == "1.0.0"

    def test_timestamp_auto_generated(self):
        """Timestamp should be auto-generated."""
        response = HealthResponse(status="healthy", version="1.0.0")
        assert response.timestamp is not None
        assert len(response.timestamp) > 0


class TestReadinessResponse:
    """Tests for ReadinessResponse model."""

    def test_valid_response(self):
        """Valid readiness response should be created."""
        response = ReadinessResponse(ready=True, message="Service ready")
        assert response.ready is True
        assert response.message == "Service ready"

    def test_with_checks(self):
        """Response with checks should work."""
        response = ReadinessResponse(ready=True, message="OK", checks={"runtime": True, "db": True})
        assert response.checks == {"runtime": True, "db": True}


class TestStateResponse:
    """Tests for StateResponse model."""

    def test_valid_response(self):
        """Valid state response should be created."""
        response = StateResponse(
            user_id="test-123",
            flow_state="active",
            active_flow="transfer",
            slots={"amount": 100},
            turn_count=3,
            waiting_for_slot=None,
        )
        assert response.user_id == "test-123"
        assert response.slots == {"amount": 100}


class TestResetResponse:
    """Tests for ResetResponse model."""

    def test_valid_response(self):
        """Valid reset response should be created."""
        response = ResetResponse(success=True, message="Conversation reset")
        assert response.success is True
        assert response.message == "Conversation reset"


class TestVersionResponse:
    """Tests for VersionResponse model."""

    def test_valid_response(self):
        """Valid version response should be created."""
        response = VersionResponse(version="1.2.3", major=1, minor=2, patch="3")
        assert response.version == "1.2.3"
        assert response.major == 1
        assert response.minor == 2
        assert response.patch == "3"

    def test_patch_can_have_suffix(self):
        """Patch version can have suffix."""
        response = VersionResponse(version="1.2.3-beta", major=1, minor=2, patch="3-beta")
        assert response.patch == "3-beta"
