"""Core type definitions for Soni v2 M1."""

from collections.abc import Awaitable, Callable
from typing import Annotated, Any, TypedDict

from langchain_core.messages import AnyMessage
from langgraph.graph.message import add_messages
from langgraph.types import Command


# =============================================================================
# REDUCERS - Specialized for proper interrupt/resume handling
# =============================================================================

def _last_value_str(current: str | None, new: str | None) -> str | None:
    """Reducer: last value wins for strings."""
    return new


def _last_value_any(current: Any, new: Any) -> Any:
    """Reducer: last value wins (generic)."""
    return new


class DialogueState(TypedDict):
    """Minimal state for M1."""
    user_message: Annotated[str | None, _last_value_str]
    messages: Annotated[list[AnyMessage], add_messages]
    response: Annotated[str | None, _last_value_str]


# =============================================================================
# NODE FUNCTION TYPE - Supports both dict returns and Command
# =============================================================================

NodeFunction = Callable[..., Awaitable[dict[str, Any] | Command]]
