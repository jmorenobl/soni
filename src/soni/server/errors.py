"""Server error handling - sanitizes errors for client responses.

Prevents exposure of sensitive information like file paths, stack traces,
and internal configuration to HTTP clients.
"""

from __future__ import annotations

import logging
import uuid
from typing import TYPE_CHECKING

from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)


# Error messages safe to expose to clients
SAFE_ERROR_MESSAGES = {
    "ConfigError": "Configuration error. Please contact support.",
    "ValidationError": "Invalid request data.",
    "FlowError": "Flow execution error. Please try again.",
    "FlowStackError": "Flow execution error. Please try again.",
    "ActionError": "Action execution failed.",
    "NLUError": "Unable to understand request. Please rephrase.",
    "StateError": "Session state error. Please start a new conversation.",
    "GraphBuildError": "Internal configuration error.",
    "SlotError": "Invalid slot value provided.",
}

DEFAULT_ERROR_MESSAGE = "An internal error occurred. Please try again later."


def create_error_reference() -> str:
    """Generate unique error reference for client/server correlation."""
    return f"ERR-{uuid.uuid4().hex[:8].upper()}"


def get_safe_error_message(exception: Exception) -> str:
    """Get client-safe error message for exception type."""
    exception_type = type(exception).__name__
    return SAFE_ERROR_MESSAGES.get(exception_type, DEFAULT_ERROR_MESSAGE)


def get_http_status_for_exception(exception: Exception) -> int:
    """Map exception types to appropriate HTTP status codes."""
    from soni.core.errors import (
        ActionError,
        ConfigError,
        FlowError,
        GraphBuildError,
        NLUError,
        SlotError,
        StateError,
        ValidationError,
    )

    # Client errors (4xx)
    if isinstance(exception, ValidationError):
        return 400
    if isinstance(exception, SlotError):
        return 422
    if isinstance(exception, NLUError):
        return 422

    # Server errors (5xx)
    if isinstance(exception, ConfigError):
        return 500
    if isinstance(exception, GraphBuildError):
        return 500
    if isinstance(exception, (FlowError, ActionError, StateError)):
        return 500

    # Default to 500 for unknown errors
    return 500


def log_error_with_context(
    error_ref: str,
    exception: Exception,
    user_id: str | None = None,
    endpoint: str | None = None,
) -> None:
    """Log full error details server-side for debugging."""
    logger.error(
        f"[{error_ref}] Error in {endpoint or 'unknown'} "
        f"for user {user_id or 'unknown'}: {type(exception).__name__}: {exception}",
        exc_info=True,
        extra={
            "error_reference": error_ref,
            "user_id": user_id,
            "endpoint": endpoint,
            "exception_type": type(exception).__name__,
        },
    )


def create_error_response(
    exception: Exception,
    user_id: str | None = None,
    endpoint: str | None = None,
) -> HTTPException:
    """Create sanitized HTTPException for client response."""
    error_ref = create_error_reference()

    # Log full details server-side
    log_error_with_context(error_ref, exception, user_id, endpoint)

    # Return sanitized response to client
    status_code = get_http_status_for_exception(exception)
    safe_message = get_safe_error_message(exception)

    return HTTPException(
        status_code=status_code,
        detail={
            "error": safe_message,
            "reference": error_ref,
            "message": "If this problem persists, contact support with the reference code.",
        },
    )


async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Global exception handler for uncaught exceptions."""
    error_ref = create_error_reference()

    # Extract user_id if available
    user_id = None
    try:
        body = await request.json()
        user_id = body.get("user_id")
    except Exception:
        pass

    log_error_with_context(error_ref, exc, user_id, request.url.path)

    return JSONResponse(
        status_code=500,
        content={
            "error": DEFAULT_ERROR_MESSAGE,
            "reference": error_ref,
            "message": "If this problem persists, contact support with the reference code.",
        },
    )
