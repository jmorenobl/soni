"""Soni FastAPI Application.

Provides REST API endpoints for the Soni dialogue system.
Uses the RuntimeLoop for dialogue processing with async support.
"""

import json
import logging
import os
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import StreamingResponse
from soni.config.loader import ConfigLoader

from soni import __version__, get_version_info
from soni.config import SoniConfig
from soni.core.errors import StateError
from soni.runtime.loop import RuntimeLoop
from soni.server.dependencies import RuntimeDep
from soni.server.errors import create_error_response, global_exception_handler
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

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan - initialize on startup, cleanup on shutdown."""
    # Get config path from environment or default
    config_path = Path(os.getenv("SONI_CONFIG_PATH", "soni.yaml"))

    if not config_path.exists():
        logger.warning(
            f"Configuration file {config_path} not found. "
            "Server will start but message processing will fail."
        )
        yield
        return

    logger.info(f"Loading configuration from {config_path}")

    try:
        config = ConfigLoader.load(config_path)
    except Exception as e:
        logger.error(f"Failed to load configuration: {e}")
        # Yield to allow startup, but runtime won't be available
        yield
        return

    try:
        # Use context manager for automatic cleanup
        async with RuntimeLoop(config) as runtime:
            # Store in app.state instead of globals
            app.state.config = config
            app.state.runtime = runtime

            logger.info("Soni server initialized successfully")
            yield

            # Context manager handles cleanup automatically

    except Exception as e:
        logger.error(f"Failed to initialize runtime: {e}")
        # If context manager entry fails (initialize raises), we yield so app can start/fail gracefully
        # depending on preference. Here we log and continue.
        yield

    logger.info("Soni server shutdown completed")

    # Clear references
    app.state.runtime = None
    app.state.config = None


# Create FastAPI app
app = FastAPI(
    title="Soni Dialogue System",
    description="A conversational AI framework using LangGraph and DSPy",
    version=__version__,
    lifespan=lifespan,
)

# Register global exception handler for uncaught exceptions
app.add_exception_handler(Exception, global_exception_handler)


@app.get("/health", response_model=HealthResponse)
async def health_check(request: Request) -> HealthResponse:
    """Liveness probe for Kubernetes.

    Returns basic health status. Use for Kubernetes liveness probes
    to detect if the process needs to be restarted.

    For detailed component status, see /ready endpoint.
    """
    runtime: RuntimeLoop | None = getattr(request.app.state, "runtime", None)

    # Determine overall status
    if runtime is None:
        status = "starting"
    elif runtime._components is None:
        status = "starting"
    elif runtime._components.graph is None:
        status = "degraded"
    else:
        status = "healthy"

    # Build component status (optional detail)
    components: dict[str, ComponentStatus] | None = None
    if runtime and runtime._components:
        components = {
            "runtime": ComponentStatus(
                name="runtime",
                status="healthy",
                message=None,
            ),
            "graph": ComponentStatus(
                name="graph",
                status="healthy" if runtime._components.graph else "unhealthy",
                message="Compiled and ready" if runtime._components.graph else "Not compiled",
            ),
            "checkpointer": ComponentStatus(
                name="checkpointer",
                status="healthy" if runtime._components.checkpointer else "degraded",
                message="Connected"
                if runtime._components.checkpointer
                else "None (in-memory only)",
            ),
        }

    return HealthResponse(
        status=status,
        version=__version__,
        timestamp=datetime.now(UTC).isoformat(),
        components=components,
    )


@app.get("/ready", response_model=ReadinessResponse)
async def readiness_check(request: Request) -> ReadinessResponse:
    """Readiness probe for Kubernetes.

    Returns 200 if the service is ready to accept traffic.
    Returns 503 if the service is not ready.

    Use this for Kubernetes readiness probes to control
    when pods receive traffic after startup or during issues.
    """
    runtime: RuntimeLoop | None = getattr(request.app.state, "runtime", None)

    checks: dict[str, bool] = {}

    # Check 1: Runtime exists
    checks["runtime_exists"] = runtime is not None

    # Check 2: Components initialized
    components_ok = False
    if runtime and runtime._components:
        components_ok = (
            runtime._components.graph is not None
            and runtime._components.du is not None
            and runtime._components.flow_manager is not None
        )
    checks["components_initialized"] = components_ok

    # Check 3: Graph is compiled (can process messages)
    checks["graph_ready"] = (
        runtime is not None
        and runtime._components is not None
        and runtime._components.graph is not None
    )

    # Overall readiness
    ready = all(checks.values())

    if not ready:
        failed_checks = [k for k, v in checks.items() if not v]
        raise HTTPException(
            status_code=503,
            detail={
                "ready": False,
                "message": f"Not ready: {', '.join(failed_checks)}",
                "checks": checks,
            },
        )

    return ReadinessResponse(
        ready=True,
        message="Service is ready to accept traffic",
        checks=checks,
    )


@app.get("/startup")
async def startup_check(request: Request) -> dict[str, bool]:
    """Startup probe for Kubernetes.

    Returns 200 once initial startup is complete.
    Use for Kubernetes startupProbe to give the app time to initialize.
    """
    runtime: RuntimeLoop | None = getattr(request.app.state, "runtime", None)

    if runtime is None or runtime._components is None:
        raise HTTPException(
            status_code=503,
            detail={"started": False, "message": "Still initializing"},
        )

    return {"started": True}


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


@app.post("/chat/stream")
async def chat_stream(
    request: MessageRequest,
    runtime: RuntimeDep,
) -> StreamingResponse:
    """Stream chat responses via Server-Sent Events.

    Emits incremental updates as each node in the graph completes.
    """
    from soni.runtime.stream_extractor import ResponseStreamExtractor

    extractor = ResponseStreamExtractor()

    async def event_generator():
        async for chunk in runtime.process_message_streaming(
            request.message,
            user_id=request.user_id,
            stream_mode="updates",
        ):
            # Extract response content
            stream_chunk = extractor.extract(chunk, "updates")
            if stream_chunk and stream_chunk.content:
                data = json.dumps(
                    {
                        "content": stream_chunk.content,
                        "node": stream_chunk.node,
                        "is_final": stream_chunk.is_final,
                    },
                    default=str,
                )
                yield f"data: {data}\n\n"

        yield "data: [DONE]\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        },
    )


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


@app.get("/version", response_model=VersionResponse)
async def get_version() -> VersionResponse:
    """Get detailed version information.

    Returns version in semantic versioning format with components.
    """
    info = get_version_info()
    return VersionResponse(
        version=info["full"],
        major=info["major"],
        minor=info["minor"],
        patch=info["patch"],
    )


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
