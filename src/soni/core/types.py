"""Core type definitions for Soni Framework.

This module defines TypedDict structures for state management that are
required by LangGraph and provide runtime type safety.
"""

from typing import TYPE_CHECKING, Any, Literal, TypeAlias, TypedDict

from soni.core.commands import Command

if TYPE_CHECKING:
    from langgraph.graph.graph import CompiledStateGraph

    # Type alias for node runtime parameter
    # Runtime is actually the compiled graph with context injected
    # Using string annotation to avoid forward reference issue
    NodeRuntime: TypeAlias = CompiledStateGraph["RuntimeContext", Any]
else:
    # At runtime, NodeRuntime is Any to avoid import overhead
    # This allows the type alias to be importable without importing langgraph
    NodeRuntime: TypeAlias = Any

# Flow states
FlowState = Literal["active", "paused", "completed", "cancelled", "abandoned", "error"]


class FlowContext(TypedDict):
    """Context for a specific instance of a flow."""

    flow_id: str
    flow_name: str
    flow_state: FlowState
    current_step: str | None
    outputs: dict[str, Any]
    started_at: float
    paused_at: float | None
    completed_at: float | None
    context: str | None


class DialogueState(TypedDict):
    """Complete dialogue state for LangGraph."""

    # User communication
    user_message: str
    last_response: str
    messages: list[dict[str, Any]]  # Will use Annotated with add_messages in Phase 4

    # Flow management
    flow_stack: list[FlowContext]
    flow_slots: dict[str, dict[str, Any]]

    # State tracking
    conversation_state: str
    current_step: str | None
    waiting_for_slot: str | None
    current_prompted_slot: str | None
    all_slots_filled: bool | None  # True when all required slots are filled

    # NLU results
    nlu_result: dict[str, Any] | None
    command_log: list[Command]  # Log of processed commands
    last_nlu_call: float | None

    # Action execution
    action_result: dict[str, Any] | None

    # Digression tracking
    digression_depth: int
    last_digression_type: str | None

    # Metadata
    turn_count: int
    trace: list[dict[str, Any]]
    metadata: dict[str, Any]


# Conversation states
ConversationState = Literal[
    "idle",
    "understanding",
    "waiting_for_slot",
    "validating_slot",
    "ready_for_action",  # Intermediate: ready to execute action
    "ready_for_confirmation",  # Intermediate: ready to ask for confirmation
    "confirming",  # Active: waiting for user confirmation response
    "executing_action",
    "completed",
    "generating_response",
    "error",
    "fallback",
]


class RuntimeContext(TypedDict):
    """Runtime context with injected dependencies.

    This context is passed to all node functions and contains configuration
    and service dependencies needed for dialogue processing.
    """

    config: Any  # SoniConfig (avoid circular import)
    scope_manager: Any  # IScopeManager
    normalizer: Any  # INormalizer
    action_handler: Any  # IActionHandler
    du: Any  # INLUProvider
    step_manager: Any  # FlowStepManager
    flow_manager: Any  # FlowManager
