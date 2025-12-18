"""Soni FastAPI Application.

Provides REST API endpoints for the Soni dialogue system.
Uses the RuntimeLoop for dialogue processing with async support.
"""

import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

from fastapi import FastAPI, Request

from soni.config import SoniConfig
from soni.config.loader import ConfigLoader
from soni.core.errors import StateError
from soni.runtime.loop import RuntimeLoop
from soni.server.dependencies import RuntimeDep
from soni.server.errors import create_error_response, global_exception_handler
from soni.server.models import (
    HealthResponse,
    MessageRequest,
    MessageResponse,
    ResetResponse,
    StateResponse,
)

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan - initialize on startup, cleanup on shutdown."""
    # Get config path from environment or default
    config_path = Path(os.getenv("SONI_CONFIG_PATH", "soni.yaml"))

    if config_path.exists():
        logger.info(f"Loading configuration from {config_path}")
        try:
            config = ConfigLoader.load(config_path)
            runtime = RuntimeLoop(config)
            await runtime.initialize()

            # Store in app.state instead of globals
            app.state.config = config
            app.state.runtime = runtime

            logger.info("Soni server initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize server: {e}")
            raise
    else:
        logger.warning(
            f"Configuration file {config_path} not found. "
            "Server will start but message processing will fail."
        )

    yield

    # Cleanup
    logger.info("Soni server shutting down")
    if hasattr(app.state, "runtime"):
        app.state.runtime = None
    if hasattr(app.state, "config"):
        app.state.config = None


# Create FastAPI app
app = FastAPI(
    title="Soni Dialogue System",
    description="A conversational AI framework using LangGraph and DSPy",
    version="0.8.0",
    lifespan=lifespan,
)

# Register global exception handler for uncaught exceptions
app.add_exception_handler(Exception, global_exception_handler)


@app.get("/health", response_model=HealthResponse)
async def health_check(request: Request) -> HealthResponse:
    """Health check endpoint.

    Returns the current health status of the server.
    """
    runtime = getattr(request.app.state, "runtime", None)

    return HealthResponse(
        status="healthy" if runtime is not None else "starting",
        version="0.8.0",
        initialized=runtime is not None,
    )


@app.post("/message", response_model=MessageResponse)
async def process_message(
    request: MessageRequest,
    runtime: RuntimeDep,
) -> MessageResponse:
    """Process a user message and return the assistant response.

    Args:
        request: Message request containing user_id and message.
        runtime: Injected RuntimeLoop dependency.

    Returns:
        Assistant's response with conversation state.
    """
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
        raise create_error_response(
            exception=e,
            user_id=request.user_id,
            endpoint="/message",
        ) from e


@app.get("/state/{user_id}", response_model=StateResponse)
async def get_conversation_state(
    user_id: str,
    runtime: RuntimeDep,
) -> StateResponse:
    """Get the current conversation state for a user.

    Args:
        user_id: Unique identifier for the conversation thread.
        runtime: Injected RuntimeLoop dependency.

    Returns:
        Current conversation state including active flow and slots.
    """
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
async def reset_conversation(
    user_id: str,
    runtime: RuntimeDep,
) -> ResetResponse:
    """Reset the conversation state for a user.

    This clears all flow state and starts fresh.

    Args:
        user_id: Unique identifier for the conversation thread.
        runtime: Injected RuntimeLoop dependency.

    Returns:
        Confirmation of reset.
    """
    try:
        was_reset = await runtime.reset_state(user_id)

        if was_reset:
            return ResetResponse(
                success=True,
                message=f"Conversation state for user '{user_id}' has been reset.",
            )
        else:
            return ResetResponse(
                success=True,
                message=f"No existing state found for user '{user_id}'.",
            )

    except StateError as e:
        raise create_error_response(
            exception=e,
            user_id=user_id,
            endpoint="/reset",
        ) from e


def create_app(config: SoniConfig | None = None) -> FastAPI:
    """Factory function to create the FastAPI app with custom config.

    Args:
        config: Optional SoniConfig. If not provided, app will load from soni.yaml.

    Returns:
        Configured FastAPI application.
    """
    if config:
        app.state.config = config
    return app
