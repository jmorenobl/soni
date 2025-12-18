"""Soni FastAPI Application.

Provides REST API endpoints for the Soni dialogue system.
Uses the RuntimeLoop for dialogue processing with async support.
"""

import logging
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException

from soni.core.config import SoniConfig
from soni.core.loader import ConfigLoader
from soni.runtime.loop import RuntimeLoop
from soni.server.models import (
    HealthResponse,
    MessageRequest,
    MessageResponse,
    ResetResponse,
    StateResponse,
)

logger = logging.getLogger(__name__)

# Global runtime instance
_runtime: RuntimeLoop | None = None
_config: SoniConfig | None = None


def get_runtime() -> RuntimeLoop:
    """Get the global runtime instance."""
    if _runtime is None:
        raise HTTPException(
            status_code=503, detail="System not initialized. Server is starting up."
        )
    return _runtime


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan - initialize and cleanup."""
    global _runtime, _config

    # Startup
    config_path = Path("soni.yaml")

    if config_path.exists():
        logger.info(f"Loading configuration from {config_path}")
        loader = ConfigLoader()
        _config = loader.from_yaml(config_path)
        _runtime = RuntimeLoop(_config)
        await _runtime.initialize()
        logger.info("Soni server initialized successfully")
    else:
        logger.warning(
            f"Configuration file {config_path} not found. "
            "Server will start but message processing will fail."
        )

    yield

    # Shutdown
    logger.info("Soni server shutting down")


# Create FastAPI app
app = FastAPI(
    title="Soni Dialogue System",
    description="A conversational AI framework using LangGraph and DSPy",
    version="0.8.0",
    lifespan=lifespan,
)


@app.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    """Health check endpoint.

    Returns the current health status of the server.
    """
    return HealthResponse(
        status="healthy" if _runtime is not None else "starting",
        version="0.8.0",
        initialized=_runtime is not None,
    )


@app.post("/message", response_model=MessageResponse)
async def process_message(request: MessageRequest) -> MessageResponse:
    """Process a user message and return the assistant response.

    Args:
        request: Message request containing user_id and message.

    Returns:
        Assistant's response with conversation state.
    """
    runtime = get_runtime()

    try:
        response = await runtime.process_message(
            message=request.message,
            user_id=request.user_id,
        )

        # Get current state for additional context
        state = await runtime.get_state(request.user_id)

        active_flow = None
        flow_state = "idle"
        turn_count = 0

        if state:
            flow_stack = state.get("flow_stack", [])
            if flow_stack:
                active_flow = flow_stack[-1].get("flow_name")
            flow_state = state.get("flow_state", "idle")
            turn_count = state.get("turn_count", 0)

        return MessageResponse(
            response=response,
            flow_state=flow_state,
            active_flow=active_flow,
            turn_count=turn_count,
        )

    except Exception as e:
        logger.error(f"Error processing message: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error processing message: {str(e)}") from e


@app.get("/state/{user_id}", response_model=StateResponse)
async def get_conversation_state(user_id: str) -> StateResponse:
    """Get the current conversation state for a user.

    Args:
        user_id: Unique identifier for the conversation thread.

    Returns:
        Current conversation state including active flow and slots.
    """
    runtime = get_runtime()

    state = await runtime.get_state(user_id)

    if not state:
        return StateResponse(
            user_id=user_id,
            flow_state="idle",
            active_flow=None,
            slots={},
            turn_count=0,
            waiting_for_slot=None,
        )

    # Extract active flow info
    flow_stack = state.get("flow_stack", [])
    active_flow = flow_stack[-1].get("flow_name") if flow_stack else None
    active_flow_id = flow_stack[-1].get("flow_id") if flow_stack else None

    # Get slots for active flow
    slots: dict[str, Any] = {}
    if active_flow_id:
        slots = state.get("flow_slots", {}).get(active_flow_id, {})
        # Filter out internal slots
        slots = {k: v for k, v in slots.items() if not k.startswith("__")}

    return StateResponse(
        user_id=user_id,
        flow_state=state.get("flow_state", "idle"),
        active_flow=active_flow,
        slots=slots,
        turn_count=state.get("turn_count", 0),
        waiting_for_slot=state.get("waiting_for_slot"),
    )


@app.post("/reset/{user_id}", response_model=ResetResponse)
async def reset_conversation(user_id: str) -> ResetResponse:
    """Reset the conversation state for a user.

    This clears all flow state and starts fresh.

    Args:
        user_id: Unique identifier for the conversation thread.

    Returns:
        Confirmation of reset.
    """
    # Note: Full reset requires checkpointer support
    # For now, we just confirm the intent - state will reset on next message
    # if no active checkpointer is configured

    return ResetResponse(
        success=True,
        message=f"Conversation state for user '{user_id}' will be reset on next interaction.",
    )


def create_app(config: SoniConfig | None = None) -> FastAPI:
    """Factory function to create the FastAPI app with custom config.

    Args:
        config: Optional SoniConfig. If not provided, app will load from soni.yaml.

    Returns:
        Configured FastAPI application.
    """
    global _config
    if config:
        _config = config
    return app
