"""Core type definitions for Soni v2 M1."""

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Annotated, Any, TypedDict

from langchain_core.messages import AnyMessage
from langgraph.graph.message import add_messages
from langgraph.types import Command

from soni.core.constants import FlowContextState


@dataclass
class FlowDelta:
    """Represents a state change to be merged."""

    flow_stack: list["FlowContext"] | None = None
    flow_slots: dict[str, dict[str, Any]] | None = None
    executed_steps: dict[str, set[str] | None] | None = None


# =============================================================================
# REDUCERS - Specialized for proper interrupt/resume handling
# =============================================================================


def _last_value_str(current: str | None, new: str | None) -> str | None:
    """Reducer that keeps the last non-None string value."""
    if new is not None:
        return new
    return current


def _last_value_any(current: Any | None, new: Any | None) -> Any | None:
    """Reducer that keeps the last non-None value."""
    if new is not None:
        return new
    return current


def _merge_flow_slots(
    current: dict[str, dict[str, Any]],
    new: dict[str, dict[str, Any]],
) -> dict[str, dict[str, Any]]:
    """Reducer that deep-merges flow_slots dicts."""
    if not current:
        current = {}
    if not new:
        return current

    result = dict(current)
    for flow_id, slots in new.items():
        if flow_id in result:
            result[flow_id] = {**result[flow_id], **slots}
        else:
            result[flow_id] = slots
    return result


def _merge_executed_steps(
    current: dict[str, set[str]],
    new: dict[str, set[str] | None],
) -> dict[str, set[str]]:
    """Reducer for executed steps. None value means clear that key."""
    if not current:
        current = {}
    if not new:
        return current

    result = dict(current)
    for flow_id, steps in new.items():
        if steps is None:
            result.pop(flow_id, None)
        else:
            existing = result.get(flow_id, set())
            result[flow_id] = existing | steps

    return result


class FlowContext(TypedDict):
    """Context for a single flow instance on the stack."""

    flow_id: str  # Unique instance ID (UUID)
    flow_name: str
    flow_state: FlowContextState
    current_step: str | None
    step_index: int


class DialogueState(TypedDict):
    """Core state schema for M2."""

    # M1 Fields
    user_message: Annotated[str | None, _last_value_str]
    messages: Annotated[list[AnyMessage], add_messages]
    response: Annotated[str | None, _last_value_str]

    # M2: Flow Management
    flow_stack: Annotated[list[FlowContext], _last_value_any]
    flow_slots: Annotated[dict[str, dict[str, Any]], _merge_flow_slots]

    # M2: Commands & Interrupts
    commands: Annotated[list[dict[str, Any]], _last_value_any]
    _need_input: Annotated[bool, _last_value_any]
    _pending_prompt: Annotated[dict[str, Any] | None, _last_value_any]

    # Internal
    _executed_steps: Annotated[dict[str, set[str]], _merge_executed_steps]
    _pending_responses: Annotated[list[str], _last_value_any]


# =============================================================================
# NODE FUNCTION TYPE - Supports both dict returns and Command
# =============================================================================

NodeFunction = Callable[..., Awaitable[dict[str, Any] | Command]]
