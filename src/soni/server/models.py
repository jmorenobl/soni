"""API Models - Pydantic models for FastAPI endpoints.

Defines request and response schemas for the Soni REST API.
"""

from pydantic import BaseModel, Field


class MessageRequest(BaseModel):
    """Request model for processing a user message."""

    user_id: str = Field(description="Unique identifier for the conversation thread")
    message: str = Field(description="User's input message")


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


class HealthResponse(BaseModel):
    """Response model for health check endpoint."""

    status: str = Field(description="Health status (healthy/unhealthy)")
    version: str = Field(description="API version")
    initialized: bool = Field(description="Whether the system is initialized")


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
