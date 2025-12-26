"""API Models - Pydantic models for FastAPI endpoints.

Defines request and response schemas for the Soni REST API.
"""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class MessageRequest(BaseModel):
    """Request model for processing a user message."""

    user_id: str = Field(description="Unique identifier for the conversation thread")
    message: str = Field(min_length=1, description="User's input message")


class MessageResponse(BaseModel):
    """Response model for processed messages."""

    response: str = Field(description="Assistant's response text")
    flow_state: str = Field(
        default="idle", description="Current flow state (idle, active, waiting_input, completed)"
    )
    active_flow: str | None = Field(
        default=None, description="Name of the currently active flow, if any"
    )
    turn_count: int = Field(default=0, description="Number of conversation turns")


class ComponentStatus(BaseModel):
    """Status of a single component."""

    name: str
    status: Literal["healthy", "degraded", "unhealthy"]
    message: str | None = None


class HealthResponse(BaseModel):
    """Health check response with component details.

    Breaking change: `initialized` field removed.
    Use `status` field or /ready endpoint instead.
    """

    status: Literal["healthy", "starting", "degraded", "unhealthy"]
    version: str
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat())
    components: dict[str, ComponentStatus] | None = None


class ReadinessResponse(BaseModel):
    """Readiness probe response."""

    ready: bool
    message: str
    checks: dict[str, bool] | None = None


class StateResponse(BaseModel):
    """Response model for conversation state endpoint."""

    user_id: str
    flow_state: str
    active_flow: str | None
    slots: dict[str, str | int | float | bool | None]
    turn_count: int
    waiting_for_slot: str | None


class ResetResponse(BaseModel):
    """Response model for reset endpoint."""

    success: bool
    message: str


class VersionResponse(BaseModel):
    """Response model for version endpoint."""

    version: str = Field(description="Full version string")
    major: int = Field(description="Major version number")
    minor: int = Field(description="Minor version number")
    patch: str = Field(description="Patch version (may include suffix)")
