"""Core type definitions for Soni v3.0.

Pure TypedDict structures for LangGraph state management.
No methods - these are data-only structures.
Uses Annotated reducers for message aggregation.
"""
from dataclasses import dataclass
from typing import Annotated, Any, Literal, TypedDict

from langchain_core.messages import AnyMessage
from langgraph.graph.message import add_messages

FlowState = Literal["idle", "active", "waiting_input", "done", "error"]


class FlowContext(TypedDict):
    """Context for a single flow instance on the stack."""
    flow_id: str  # Unique instance ID (UUID)
    flow_name: str  # Flow definition name
    flow_state: Literal["active", "completed", "cancelled"]
    current_step: str | None  # Current step name
    step_index: int  # Current step index
    outputs: dict[str, Any]  # Flow outputs
    started_at: float  # Timestamp


class DialogueState(TypedDict):
    """Complete dialogue state for LangGraph.

    This is the single source of truth for conversation state.
    All nodes read from and write to this structure.

    Uses Annotated reducers:
    - messages: Uses add_messages for proper message aggregation
    """

    # User communication (with reducer for message accumulation)
    user_message: str | None
    last_response: str
    messages: Annotated[list[AnyMessage], add_messages]  # Reducer for messages

    # Flow management
    flow_stack: list[FlowContext]
    flow_slots: dict[str, dict[str, Any]]  # flow_id -> slot_name -> value

    # State tracking
    flow_state: FlowState
    waiting_for_slot: str | None

    # Commands from NLU (replaced each turn, no reducer)
    commands: list[dict[str, Any]]  # Serialized commands

    # Transient data
    response: str | None
    action_result: dict[str, Any] | None

    # Metadata
    turn_count: int
    metadata: dict[str, Any]




@dataclass
class RuntimeContext:
    """Runtime context with injected dependencies.

    Passed to nodes via LangGraph's context injection.
    """

    config: Any  # SoniConfig
    flow_manager: Any  # FlowManager
    action_handler: Any  # ActionHandler
    du: Any  # NLU provider
