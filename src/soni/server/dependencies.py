"""FastAPI dependencies for server endpoints.

Uses dependency injection instead of global state for better
testability and multi-worker safety.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Annotated, cast

from fastapi import Depends, HTTPException, Request

if TYPE_CHECKING:
    from soni.core.config import SoniConfig
    from soni.runtime.loop import RuntimeLoop


def get_runtime(request: Request) -> RuntimeLoop:
    """Dependency to get initialized RuntimeLoop.

    Raises:
        HTTPException: 503 if runtime not initialized
    """
    runtime = getattr(request.app.state, "runtime", None)

    if runtime is None:
        raise HTTPException(
            status_code=503,
            detail={
                "error": "Service temporarily unavailable",
                "message": "Server is starting up. Please try again in a few seconds.",
            },
        )

    # Import at runtime to avoid circular imports
    from soni.runtime.loop import RuntimeLoop as RuntimeLoopClass

    return cast(RuntimeLoopClass, runtime)


def get_config(request: Request) -> SoniConfig:
    """Dependency to get loaded configuration.

    Raises:
        HTTPException: 503 if config not loaded
    """
    config = getattr(request.app.state, "config", None)

    if config is None:
        raise HTTPException(
            status_code=503,
            detail={
                "error": "Service not configured",
                "message": "Server configuration not loaded.",
            },
        )

    # Import at runtime to avoid circular imports
    from soni.core.config import SoniConfig as SoniConfigClass

    return cast(SoniConfigClass, config)


# Type aliases for cleaner endpoint signatures
RuntimeDep = Annotated["RuntimeLoop", Depends(get_runtime)]
ConfigDep = Annotated["SoniConfig", Depends(get_config)]
