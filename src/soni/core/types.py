"""Core type definitions for Soni v3.0.

Simplified TypedDict structures for LangGraph state management.
"""

from typing import Any, Literal, TypedDict

from soni.core.commands import Command

# Flow states for FlowContext
FlowContextState = Literal["active", "completed", "cancelled"]

# Backward compatibility alias for old code that imports FlowState
FlowState = Literal["active", "paused", "completed", "cancelled", "abandoned", "error"]


class FlowContext(TypedDict):
    """Context for a flow instance on the stack."""
    
    flow_id: str
    flow_name: str
    flow_state: FlowContextState
    current_step: str | None
    outputs: dict[str, Any]
    started_at: float


class DialogueState(TypedDict):
    """Complete dialogue state for LangGraph v3.0.
    
    Simplified from v2.0 - removed legacy fields.
    """
    
    # User communication
    user_message: str
    last_response: str
    messages: list[dict[str, Any]]
    
    # Flow management
    flow_stack: list[FlowContext]
    flow_slots: dict[str, dict[str, Any]]  # flow_id -> slot_name -> value
    
    # State tracking
    flow_state: str  # FlowState enum value
    waiting_for_slot: str | None
    
    # Commands from NLU
    commands: list[Command]
    
    # Transient response (used between step and respond nodes)
    response: str | None
    
    # Action results
    action_result: dict[str, Any] | None
    
    # Metadata
    turn_count: int
    metadata: dict[str, Any]


class RuntimeContext(TypedDict):
    """Runtime context with injected dependencies."""
    
    config: Any  # SoniConfig
    scope_manager: Any  # IScopeManager
    action_handler: Any  # IActionHandler
    du: Any  # INLUProvider
    step_manager: Any  # FlowStepManager
    flow_manager: Any  # FlowManager
