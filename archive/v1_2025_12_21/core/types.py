"""Core type definitions for Soni v3.0.

Pure TypedDict structures for LangGraph state management.
No methods - these are data-only structures.
Uses Annotated reducers for message aggregation.

Protocols are defined here to avoid circular imports while
maintaining full type safety for RuntimeContext dependencies.
"""

from dataclasses import dataclass
from typing import Annotated, Any, Protocol, TypedDict, runtime_checkable

from langchain_core.messages import AnyMessage
from langgraph.graph.message import add_messages

from soni.core.constants import FlowContextState, FlowState, SlotWaitType

# Forward reference for Protocol definitions
# (Actual SoniConfig imported at runtime if needed)


class FlowContext(TypedDict):
    """Context for a single flow instance on the stack."""

    flow_id: str  # Unique instance ID (UUID)
    flow_name: str  # Flow definition name
    flow_state: FlowContextState
    current_step: str | None  # Current step name
    step_index: int  # Current step index
    outputs: dict[str, Any]  # Flow outputs
    started_at: float  # Timestamp


@dataclass
class FlowDelta:
    """State delta returned by FlowManager mutation methods.

    Callers must merge these into their return dict for LangGraph to track.
    This follows the immutable state pattern where mutations return deltas
    instead of modifying state in-place.

    Attributes:
        flow_stack: Updated flow stack if changed, None if unchanged.
        flow_slots: Updated slot mapping if changed, None if unchanged.
    """

    flow_stack: list[FlowContext] | None = None
    flow_slots: dict[str, dict[str, Any]] | None = None
    executed_steps: dict[str, set[str]] | None = None


def _last_value_str(current: str | None, new: str | None) -> str | None:
    """Reducer that always returns the new value (last write wins).

    Used for user_message to handle concurrent updates during interrupt/resume.
    When Command(resume=..., update={user_message: ...}) is used, LangGraph
    may detect concurrent updates with the checkpoint. This reducer resolves
    the conflict by always taking the new value.
    """
    return new


def _last_value_int(current: int, new: int) -> int:
    """Reducer that always returns the new value (last write wins) for int fields.

    Used for turn_count during interrupt/resume.
    """
    return new


def _last_value_list(current: list[Any], new: list[Any]) -> list[Any]:
    """Reducer that always returns the new list (last write wins).

    Used for commands during interrupt/resume.
    """
    return new


def _last_value_any(current: Any, new: Any) -> Any:
    """Generic reducer that always returns the new value (last write wins).

    Used for various fields that may have concurrent updates during resume:
    flow_state, waiting_for_slot, response, action_result, metadata, etc.
    """
    return new


def _merge_flow_slots(
    current: dict[str, dict[str, Any]],
    new: dict[str, dict[str, Any]],
) -> dict[str, dict[str, Any]]:
    """Reducer that deep-merges flow_slots dicts.

    Each flow_id maps to a dict of slot values. This reducer:
    - Preserves existing flow_ids not in 'new'
    - For overlapping flow_ids, merges the slot dicts (new values override)

    This is critical for interrupt/resume: the collect_node updates one
    slot at a time, and we need to preserve existing slots.
    """
    # Debug logging for reducer (disabled)
    # print(f"[REDUCER] merge_flow_slots called")
    # print(f"  Current keys: {list(current.keys())} with slots: {current}")
    # print(f"  New keys: {list(new.keys())} with slots: {new}")

    result = dict(current)  # Shallow copy of outer dict
    for flow_id, slots in new.items():
        if flow_id in result:
            # Merge slots for existing flow
            # print(f"  Merging flow {flow_id}: current={result[flow_id].keys()}, new={slots.keys()}")
            result[flow_id] = {**result[flow_id], **slots}
            # print(f"  Result: {result[flow_id]}")
        else:
            # print(f"  New flow {flow_id}: {slots}")
            result[flow_id] = slots
    return result


def _merge_dicts(
    current: dict[str, Any],
    new: dict[str, Any],
) -> dict[str, Any]:
    """Reducer that merges dictionaries.

    Supports deletion: if value is None, key is removed from result.
    Used for _executed_steps cleanup.
    """
    result = dict(current)
    for key, value in new.items():
        if value is None:
            result.pop(key, None)
        elif key in result and isinstance(result[key], set) and isinstance(value, set):
            result[key] = result[key] | value
        else:
            result[key] = value
    return result


class DialogueState(TypedDict):
    """Complete dialogue state for LangGraph.

    This is the single source of truth for conversation state.
    All nodes read from and write to this structure.

    Uses Annotated reducers:
    - messages: Uses add_messages for proper message aggregation
    - user_message: Uses _last_value_str for interrupt/resume support
    - turn_count: Uses _last_value_int for interrupt/resume support
    - commands: Uses _last_value_list for interrupt/resume support
    - flow_slots: Uses _merge_flow_slots for proper slot persistence
    """

    # User communication (with reducers for proper state handling)
    user_message: Annotated[str | None, _last_value_str]  # Last value wins on resume
    last_response: Annotated[str, _last_value_str]  # Last value wins on concurrent updates
    messages: Annotated[list[AnyMessage], add_messages]  # Reducer for messages

    # Flow management
    flow_stack: list[FlowContext]
    flow_slots: Annotated[
        dict[str, dict[str, Any]], _merge_flow_slots
    ]  # flow_id -> slot_name -> value (with merge reducer)

    # State tracking (with reducers for resume pattern)
    flow_state: Annotated[FlowState, _last_value_any]  # Last value wins
    waiting_for_slot: Annotated[str | None, _last_value_any]  # Last value wins
    waiting_for_slot_type: Annotated[
        SlotWaitType | None, _last_value_any
    ]  # CONFIRMATION | COLLECTION

    # Commands from NLU (replaced each turn)
    commands: Annotated[list[dict[str, Any]], _last_value_list]  # Last value wins on resume

    # Transient data (with reducers for resume pattern)
    response: Annotated[str | None, _last_value_any]  # Last value wins
    action_result: Annotated[dict[str, Any] | None, _last_value_any]  # Last value wins
    _branch_target: Annotated[str | None, _last_value_any]  # Target node for branch routing
    _digression_pending: Annotated[bool, _last_value_any]  # Flag for digression during interrupt
    _pending_responses: Annotated[list[str], _last_value_any]  # Queue of responses to show
    _pending_prompt: Annotated[
        dict[str, Any] | None, _last_value_any
    ]  # Prompt info for request_input_node

    # NEW: Interrupt Architecture fields
    _need_input: Annotated[bool, _last_value_any]  # Flag from subgraph

    # Idempotency tracking (flow_id -> set of executed steps)
    _executed_steps: Annotated[dict[str, set[str]], _merge_dicts]

    # Metadata
    turn_count: Annotated[int, _last_value_int]  # Last value wins on resume
    metadata: Annotated[dict[str, Any], _last_value_any]  # Last value wins


# =============================================================================
# PROTOCOLS - Structural typing for dependency injection
#
# Following Interface Segregation Principle (ISP), FlowManager capabilities
# are split into focused protocols. Components can depend only on what they need.
# =============================================================================


@runtime_checkable
class SlotProvider(Protocol):
    """Protocol for slot read/write operations.

    Use when component only needs to read or modify slot values,
    not manage flow stack or control flow execution.
    """

    def set_slot(
        self, state: DialogueState, slot_name: str, value: Any
    ) -> FlowDelta | None:  # Returns FlowDelta or None
        """Set a slot value in the active flow context."""
        ...

    def get_slot(self, state: DialogueState, slot_name: str) -> Any:
        """Get a slot value from the active flow context."""
        ...

    def get_all_slots(self, state: DialogueState) -> dict[str, Any]:
        """Get all slots for the active flow."""
        ...


@runtime_checkable
class FlowStackProvider(Protocol):
    """Protocol for flow stack operations.

    Use when component needs to push/pop flows or handle intent changes.
    """

    def push_flow(
        self,
        state: DialogueState,
        flow_name: str,
        inputs: dict[str, Any] | None = None,
    ) -> tuple[str, FlowDelta]:  # Returns (flow_id, FlowDelta)
        """Push a new flow onto the stack."""
        ...

    def pop_flow(
        self,
        state: DialogueState,
        result: FlowContextState = FlowContextState.COMPLETED,
    ) -> tuple[FlowContext, FlowDelta]:  # Returns (popped_context, FlowDelta)
        """Pop the top flow from the stack."""
        ...

    def handle_intent_change(
        self,
        state: DialogueState,
        new_flow: str,
    ) -> FlowDelta | None:  # Returns FlowDelta or None
        """Handle intent switch (push new flow)."""
        ...


@runtime_checkable
class FlowContextProvider(Protocol):
    """Protocol for flow context read and step advancement.

    Use when component needs to inspect or advance flow execution.
    """

    def get_active_context(self, state: DialogueState) -> FlowContext | None:
        """Get the currently active flow context."""
        ...

    def advance_step(self, state: DialogueState) -> FlowDelta | None:  # Returns FlowDelta or None
        """Advance to next step in current flow."""
        ...

    def get_active_flow_id(self, state: DialogueState) -> str | None:
        """Get the ID of the active flow."""
        ...


@runtime_checkable
class FlowManagerProtocol(SlotProvider, FlowStackProvider, FlowContextProvider, Protocol):
    """Full FlowManager protocol - combines all capabilities.

    For backwards compatibility and cases where full access is needed.
    Prefer using specific protocols (SlotProvider, etc.) when possible.

    All mutation methods return FlowDelta objects instead of modifying
    state in-place. This ensures LangGraph properly tracks changes.
    """

    pass  # All methods inherited from parent protocols


@runtime_checkable
class ActionHandlerProtocol(Protocol):
    """Protocol for ActionHandler."""

    async def execute(self, action_name: str, inputs: dict[str, Any]) -> dict[str, Any]:
        """Execute a registered action with validation."""
        ...


@runtime_checkable
class DUProtocol(Protocol):
    """Protocol for Dialogue Understanding (NLU) module."""

    async def acall(
        self,
        user_message: str,
        context: Any,  # DialogueContext from du.models
        history: list[dict[str, str]] | None = None,
    ) -> Any:
        """Extract commands from user message (async)."""
        ...


@runtime_checkable
class SlotExtractorProtocol(Protocol):
    """Protocol for slot extraction (Pass 2 of two-pass NLU)."""

    async def acall(
        self,
        user_message: str,
        slot_definitions: list[Any],  # SlotExtractionInput from du.slot_extractor
    ) -> list[Any]:
        """Extract slot values from user message given slot definitions."""
        ...


@runtime_checkable
class NLUServiceProtocol(Protocol):
    """Protocol for NLU Service (orchestrator level)."""

    async def process_message(
        self,
        message: str,
        state: DialogueState,
        context: Any,  # RuntimeContext
    ) -> Any:  # Returns NLUOutput
        """Process a message through the NLU pipeline."""
        ...

    def serialize_commands(self, commands: list[Any]) -> list[dict[str, Any]]:
        """Serialize NLU commands for storage in state."""
        ...


@runtime_checkable
class ConfigProtocol(Protocol):
    """Protocol for SoniConfig."""

    @property
    def flows(self) -> dict[str, Any]:
        """Access flow configurations."""
        ...

    @property
    def slots(self) -> dict[str, Any]:
        """Access global slot definitions."""
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
    # du and slot_extractor deprecated, use nlu_service
    du: DUProtocol
    slot_extractor: SlotExtractorProtocol | None = None

    # NEW: Services
    nlu_service: Any = None  # Typed as Any to avoid importing NLUServiceProtocol (circular)
    subgraphs: dict[str, Any] | None = (
        None  # dict[str, CompiledStateGraph]  # Optional for backwards compat
    )


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================
