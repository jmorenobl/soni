"""Soni FastAPI Application.

Provides REST API endpoints for the Soni dialogue system.
Uses the RuntimeLoop for dialogue processing with async support.
"""

import logging
import os
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Literal

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from soni import __version__
from soni.actions.registry import ActionRegistry
from soni.config import SoniConfig
from soni.core.errors import SoniError, StateError
from soni.server.dependencies import RuntimeDep
from soni.server.errors import global_exception_handler
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
    from dotenv import load_dotenv

    load_dotenv()

    config_path = os.environ.get("SONI_CONFIG_PATH")
    if not config_path:
        default_path = "soni.yaml"
        if os.path.exists(default_path):
            config_path = default_path

    if not config_path:
        logger.warning(
            "SONI_CONFIG_PATH not set and soni.yaml not found. App will start unconfigured."
        )
        yield
        return

    logger.info(f"Loading config from {config_path}")
    try:
        from soni.config.loader import ConfigLoader

        config = ConfigLoader.load(config_path)
    except Exception as e:
        logger.error(f"Failed to load config: {e}")
        yield
        return

    # Checkpointer
    from langgraph.checkpoint.base import BaseCheckpointSaver
    from langgraph.checkpoint.memory import MemorySaver
    from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver

    persistence_cfg = config.settings.persistence
    checkpointer: BaseCheckpointSaver | None = None

    # Initialize RuntimeLoop
    from soni.runtime.loop import RuntimeLoop

    logger.info("Initializing RuntimeLoop...")

    # Context managers
    checkpointer_cm = None

    try:
        if persistence_cfg.backend == "sqlite":
            checkpointer_cm = AsyncSqliteSaver.from_conn_string(persistence_cfg.path)
            checkpointer = await checkpointer_cm.__aenter__()
        else:
            checkpointer = MemorySaver()

        # Configure DSPy
        from soni.core.dspy_service import DSPyBootstrapper

        DSPyBootstrapper.bootstrap(config)

        async with RuntimeLoop(
            config, checkpointer, action_registry=ActionRegistry.get_default()
        ) as runtime:
            app.state.runtime = runtime
            app.state.config = config
            logger.info("RuntimeLoop initialized and ready.")
            yield
            logger.info("RuntimeLoop cleanup...")

    except Exception as e:
        logger.error(f"RuntimeLoop initialization failed: {e}")
        yield
    finally:
        if checkpointer_cm:
            await checkpointer_cm.__aexit__(None, None, None)


# Create FastAPI app
app = FastAPI(
    title="Soni Dialogue System",
    description="A conversational AI framework using LangGraph and DSPy",
    version=__version__,
    lifespan=lifespan,
)

app.add_exception_handler(Exception, global_exception_handler)


@app.get("/health", response_model=HealthResponse)
async def health_check(request: Request) -> HealthResponse:
    """Liveness probe for Kubernetes."""
    runtime = getattr(request.app.state, "runtime", None)

    # Basic component status
    components: dict[str, ComponentStatus] = {}
    status: Literal["healthy", "starting", "degraded", "unhealthy"] = "healthy"

    if not runtime:
        status = "starting"

    return HealthResponse(
        status=status,
        version=__version__,
        timestamp=datetime.now().isoformat(),
        components=components,
    )


@app.get("/ready", response_model=ReadinessResponse)
async def readiness_check(request: Request) -> ReadinessResponse:
    """Readiness probe for Kubernetes."""
    runtime = getattr(request.app.state, "runtime", None)

    if not runtime:
        return ReadinessResponse(
            ready=False, message="Runtime not initialized", checks={"runtime": False}
        )

    return ReadinessResponse(ready=True, message="Service is ready", checks={"runtime": True})


@app.get("/startup")
async def startup_check(request: Request) -> JSONResponse:
    """Startup probe for Kubernetes."""
    runtime = getattr(request.app.state, "runtime", None)
    if runtime:
        return JSONResponse(status_code=200, content={"status": "started"})
    return JSONResponse(status_code=503, content={"status": "starting"})


@app.post("/chat", response_model=MessageResponse)
async def process_message(
    request: MessageRequest,
    runtime: RuntimeDep,
) -> MessageResponse:
    """Process a user message and return the assistant response."""
    try:
        response_data = await runtime.process_message(request.message, user_id=request.user_id)

        response_text = ""
        # Handle response types
        if isinstance(response_data, dict):
            response_text = str(response_data.get("response", ""))
        else:
            response_text = str(response_data)

        # In M10, detailed flow state tracking in API response might be simplified
        return MessageResponse(
            response=response_text,
            flow_state="active",  # placeholder
            active_flow=None,  # placeholder
            turn_count=0,  # placeholder
        )
    except StateError as e:
        logger.warning(f"State error for user {request.user_id}: {e}")
        return MessageResponse(
            response="I'm having trouble accessing your conversation history.", flow_state="error"
        )
    except Exception as e:
        logger.exception(f"Error processing message for user {request.user_id}")
        raise SoniError(f"Error processing message: {str(e)}") from e


@app.get("/state/{user_id}", response_model=StateResponse)
async def get_conversation_state(
    user_id: str,
    runtime: RuntimeDep,
) -> StateResponse:
    """Get the current conversation state for a user."""
    # Placeholder for M10 - actual deep state inspection requires LangGraph access
    # which is not fully exposed in RuntimeLoop public API yet
    return StateResponse(
        user_id=user_id,
        flow_state="active",
        active_flow="unknown",
        slots={},
        turn_count=0,
        waiting_for_slot=None,
    )


@app.delete("/state/{user_id}", response_model=ResetResponse)
async def reset_conversation(
    user_id: str,
    runtime: RuntimeDep,
) -> ResetResponse:
    """Reset the conversation state for a user."""
    # Placeholder for M10
    # RuntimeLoop doesn't expose reset_state() yet
    return ResetResponse(success=False, message="Reset not implemented in M10 runtime")


@app.get("/version", response_model=VersionResponse)
def get_version() -> VersionResponse:
    """Get detailed version information."""
    parts = __version__.split(".")
    major = int(parts[0]) if len(parts) > 0 and parts[0].isdigit() else 0
    minor = int(parts[1]) if len(parts) > 1 and parts[1].isdigit() else 0
    patch = parts[2] if len(parts) > 2 else "0"

    return VersionResponse(version=__version__, major=major, minor=minor, patch=patch)


def create_app(config: SoniConfig | None = None) -> FastAPI:
    """Factory function."""
    if config:
        app.state.config = config
    return app
