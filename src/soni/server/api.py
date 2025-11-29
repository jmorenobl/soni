"""FastAPI server for Soni Framework"""

import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from soni.core.errors import NLUError, SoniError, ValidationError
from soni.runtime import RuntimeLoop

logger = logging.getLogger(__name__)

# Global runtime instance (will be initialized in lifespan)
runtime: RuntimeLoop | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan context manager for FastAPI app.

    Handles startup and shutdown events.

    Args:
        app: FastAPI application instance
    """
    # Startup
    global runtime

    # Get config path from environment or use default
    config_path_str = os.getenv("SONI_CONFIG_PATH", "examples/flight_booking/soni.yaml")
    config_path = Path(config_path_str)

    if not config_path.exists():
        logger.error(f"Configuration file not found: {config_path}")
        raise FileNotFoundError(f"Configuration file not found: {config_path}")

    # Get optimized DU path from environment (optional)
    optimized_du_path = os.getenv("SONI_OPTIMIZED_DU_PATH")
    if optimized_du_path:
        optimized_du_path_obj = Path(optimized_du_path)
        if optimized_du_path_obj.exists():
            runtime = RuntimeLoop(config_path, optimized_du_path=optimized_du_path_obj)
            logger.info(f"RuntimeLoop initialized with optimized DU: {optimized_du_path}")
        else:
            logger.warning(f"Optimized DU path not found: {optimized_du_path}, using default")
            runtime = RuntimeLoop(config_path)
    else:
        runtime = RuntimeLoop(config_path)

    logger.info(f"RuntimeLoop initialized with config: {config_path}")

    yield

    # Shutdown
    logger.info("Shutting down Soni server")
    if runtime:
        await runtime.cleanup()
    runtime = None


# Create FastAPI app
app = FastAPI(
    title="Soni Framework API",
    description="Open Source Conversational AI Framework",
    version="0.1.0",
    lifespan=lifespan,
)


# Request/Response models
class ChatRequest(BaseModel):
    """Request model for chat endpoint"""

    message: str = Field(..., description="User message to process", min_length=1)


class ChatResponse(BaseModel):
    """Response model for chat endpoint"""

    response: str = Field(..., description="System response")
    user_id: str = Field(..., description="User ID")


class HealthResponse(BaseModel):
    """Response model for health endpoint"""

    status: str = Field(..., description="Service status")
    version: str = Field(..., description="API version")


# Exception handlers
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    """Handle request validation errors"""
    logger.warning(f"Validation error in {request.url.path}: {exc.errors()}")
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"detail": exc.errors()},
    )


@app.exception_handler(SoniError)
async def soni_error_handler(request: Request, exc: SoniError) -> JSONResponse:
    """Handle Soni framework errors"""
    logger.error(f"Soni error in {request.url.path}: {exc}")
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": str(exc)},
    )


@app.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    """
    Health check endpoint.

    Returns:
        Health status and API version
    """
    return HealthResponse(status="ok", version="0.1.0")


@app.post("/chat/{user_id}", response_model=ChatResponse)
async def chat(user_id: str, request: ChatRequest) -> ChatResponse:
    """
    Process a user message and return response.

    Args:
        user_id: Unique identifier for user/conversation
        request: Chat request with user message

    Returns:
        Chat response with system message

    Raises:
        HTTPException: If processing fails
    """
    # Validate user_id
    if not user_id or not user_id.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User ID cannot be empty",
        )

    if runtime is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Runtime not initialized",
        )

    try:
        logger.info(
            f"Processing message for user {user_id}",
            extra={"user_id": user_id, "message_length": len(request.message)},
        )

        # Process message
        response_text = await runtime.process_message(
            user_msg=request.message,
            user_id=user_id,
        )

        logger.info(f"Successfully processed message for user {user_id}")
        return ChatResponse(response=response_text, user_id=user_id)

    except ValidationError as e:
        logger.warning(f"Validation error for user {user_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e
    except NLUError as e:
        logger.error(f"NLU error for user {user_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Natural language understanding failed",
        ) from e
    except SoniError as e:
        logger.error(f"Soni error for user {user_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Processing failed: {str(e)}",
        ) from e
    except Exception as e:
        logger.error(f"Unexpected error for user {user_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error",
        ) from e
