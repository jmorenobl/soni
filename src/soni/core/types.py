"""Core type definitions for Soni v3.0.

Pure TypedDict structures for LangGraph state management.
No methods - these are data-only structures.
Uses Annotated reducers for message aggregation.

Protocols are defined here to avoid circular imports while
maintaining full type safety for RuntimeContext dependencies.
"""

from dataclasses import dataclass
from typing import Annotated, Any, Literal, Protocol, TypedDict, runtime_checkable

from langchain_core.messages import AnyMessage
from langgraph.graph.message import add_messages

# Forward reference for Protocol definitions
# (Actual SoniConfig imported at runtime if needed)

FlowState = Literal["idle", "active", "waiting_input", "done", "error"]
FlowContextState = Literal["active", "completed", "cancelled"]


class FlowContext(TypedDict):
    """Context for a single flow instance on the stack."""

    flow_id: str  # Unique instance ID (UUID)
    flow_name: str  # Flow definition name
    flow_state: FlowContextState
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
    _branch_target: str | None  # Target node for branch routing

    # Metadata
    turn_count: int
    metadata: dict[str, Any]


# =============================================================================
# PROTOCOLS - Structural typing for dependency injection
# =============================================================================


@runtime_checkable
class FlowManagerProtocol(Protocol):
    """Protocol for FlowManager - enables DI without circular imports."""

    async def push_flow(
        self,
        state: DialogueState,
        flow_name: str,
        inputs: dict[str, Any] | None = None,
    ) -> str:
        """Push a new flow onto the stack."""
        ...

    async def pop_flow(
        self,
        state: DialogueState,
        result: FlowContextState = "completed",
    ) -> FlowContext:
        """Pop the top flow from the stack."""
        ...

    async def handle_intent_change(
        self,
        state: DialogueState,
        new_flow: str,
    ) -> None:
        """Handle intent switch (push new flow)."""
        ...

    def get_active_context(self, state: DialogueState) -> FlowContext | None:
        """Get the currently active flow context."""
        ...

    async def set_slot(self, state: DialogueState, slot_name: str, value: Any) -> None:
        """Set a slot value in the active flow context."""
        ...

    def get_slot(self, state: DialogueState, slot_name: str) -> Any:
        """Get a slot value from the active flow context."""
        ...

    def get_all_slots(self, state: DialogueState) -> dict[str, Any]:
        """Get all slots for the active flow."""
        ...

    async def advance_step(self, state: DialogueState) -> bool:
        """Advance to next step in current flow."""
        ...


@runtime_checkable
class ActionHandlerProtocol(Protocol):
    """Protocol for ActionHandler."""

    async def execute(self, action_name: str, inputs: dict[str, Any]) -> dict[str, Any]:
        """Execute a registered action with validation."""
        ...


@runtime_checkable
class DUProtocol(Protocol):
    """Protocol for Dialogue Understanding (NLU) module."""

    async def aforward(
        self,
        user_message: str,
        context: Any,  # DialogueContext from du.models
        history: list[dict[str, str]] | None = None,
    ) -> Any:
        """Extract commands from user message (async)."""
        ...


@runtime_checkable
class ConfigProtocol(Protocol):
    """Protocol for SoniConfig."""

    @property
    def flows(self) -> dict[str, Any]:
        """Access flow configurations."""
        ...


# =============================================================================
# RUNTIME CONTEXT - Fully typed using Protocols
# =============================================================================


@dataclass
class RuntimeContext:
    """Runtime context with injected dependencies.

    Passed to nodes via LangGraph's context injection.

    All fields are now properly typed using Protocols to avoid
    circular imports while maintaining full type safety.
    """

    config: ConfigProtocol
    flow_manager: FlowManagerProtocol
    action_handler: ActionHandlerProtocol
    du: DUProtocol


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================


def get_runtime_context(config: Any) -> RuntimeContext:
    """Extract RuntimeContext from LangGraph RunnableConfig.

    This helper reduces boilerplate in node implementations by providing
    a single point of access to the runtime context.

    Args:
        config: RunnableConfig passed to node functions.

    Returns:
        RuntimeContext with injected dependencies.

    Raises:
        KeyError: If runtime_context is not found in config.

    Example:
        async def my_node(state: DialogueState, config: RunnableConfig) -> dict:
            context = get_runtime_context(config)
            fm = context.flow_manager
            ...
    """
    context: RuntimeContext = config["configurable"]["runtime_context"]
    return context
