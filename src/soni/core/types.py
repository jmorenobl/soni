"""Core type definitions for Soni v2 M1."""

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Annotated, Any, TypedDict

from langchain_core.messages import AnyMessage
from langgraph.graph.message import add_messages
from langgraph.types import Command

from soni.core.constants import FlowContextState
from soni.core.pending_task import PendingTask
from soni.core.slot_utils import deep_merge_flow_slots


@dataclass
class FlowDelta:
    """Represents a state change to be merged."""

    flow_stack: list["FlowContext"] | None = None
    flow_slots: dict[str, dict[str, Any]] | None = None
    executed_steps: dict[str, set[str] | None] | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert delta to state update dictionary."""
        updates: dict[str, Any] = {}
        if self.flow_stack is not None:
            updates["flow_stack"] = self.flow_stack
        if self.flow_slots is not None:
            updates["flow_slots"] = self.flow_slots
        if self.executed_steps is not None:
            updates["_executed_steps"] = self.executed_steps
        return updates


def merge_deltas(deltas: list[FlowDelta]) -> FlowDelta:
    """Merge multiple deltas into one (last one wins for stack, merged for slots)."""
    merged = FlowDelta()
    for d in deltas:
        if d.flow_stack is not None:
            merged.flow_stack = d.flow_stack
        if d.flow_slots is not None:
            if merged.flow_slots is None:
                merged.flow_slots = {}
            merged.flow_slots = deep_merge_flow_slots(merged.flow_slots, d.flow_slots)
        if d.executed_steps is not None:
            if merged.executed_steps is None:
                merged.executed_steps = {}
            merged.executed_steps.update(d.executed_steps)
    return merged


# =============================================================================
# REDUCERS - Specialized for proper interrupt/resume handling
# =============================================================================


def _last_value_str(current: str | None, new: str | None) -> str | None:
    """Reducer that keeps the last value (including None to clear)."""
    # Note: This reducer is designed to allow clearing via explicit None.
    # If a node returns {key: None}, it will clear the value.
    return new


def _last_value_any(current: Any | None, new: Any | None) -> Any | None:
    """Reducer that keeps the last value (allows None to clear)."""
    return new


def _merge_flow_slots(
    current: dict[str, dict[str, Any]],
    new: dict[str, dict[str, Any]],
) -> dict[str, dict[str, Any]]:
    """Reducer that deep-merges flow_slots dicts."""
    if not current:
        current = {}
    if not new:
        return current

    return deep_merge_flow_slots(current, new)


def add_responses(current: list[str] | None, new: list[str] | None) -> list[str]:
    """Reducer that accumulates responses."""
    if current is None:
        current = []
    if new is None:
        return current
    return current + new


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
    flow_stack: Annotated[list[FlowContext] | None, _last_value_any]
    flow_slots: Annotated[dict[str, dict[str, Any]] | None, _merge_flow_slots]

    # M2: Commands & Interrupts
    commands: Annotated[list[dict[str, Any]] | None, _last_value_any]
    _pending_task: Annotated[PendingTask | None, _last_value_any]

    # Internal
    _executed_steps: Annotated[dict[str, set[str]] | None, _merge_executed_steps]
    _branch_target: Annotated[str | None, _last_value_str]  # M6: Branching
    _flow_changed: Annotated[bool | None, _last_value_any]

    # M7 Orchestration
    _loop_flag: Annotated[bool | None, _last_value_any]  # M6: Link/Call signal
    _pending_responses: Annotated[list[str], add_responses]


# =============================================================================
# NODE FUNCTION TYPE - Supports both dict returns and Command
# =============================================================================

NodeFunction = Callable[..., Awaitable[dict[str, Any] | Command]]
