"""Core type definitions for Soni Framework.

This module defines TypedDict structures for state management that are
required by LangGraph and provide runtime type safety.
"""

from typing import Any, Literal, TypedDict

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

    # NLU results
    nlu_result: dict[str, Any] | None
    last_nlu_call: float | None

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
    "collecting",
    "executing_action",
    "generating_response",
    "error",
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
