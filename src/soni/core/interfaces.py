"""Core interfaces (Protocols) for Soni Framework following SOLID principles."""

from typing import TYPE_CHECKING, Any, Protocol

from soni.core.types import DialogueState as DialogueStateTypedDict
from soni.core.types import FlowContext

if TYPE_CHECKING:
    from soni.core.state import DialogueState as DialogueStateDataclass

    DialogueState = DialogueStateTypedDict | DialogueStateDataclass | dict[str, Any]
else:
    # Runtime: use TypedDict version for Protocol compatibility
    # The actual implementation will handle both types
    DialogueState = DialogueStateTypedDict | dict[str, Any]


class INLUProvider(Protocol):
    """Interface for NLU providers."""

    async def understand(
        self,
        user_message: str,
        dialogue_context: dict[str, Any],
    ) -> dict[str, Any]:
        """Understand user message and return NLU result."""
        ...


class IActionHandler(Protocol):
    """Interface for action execution."""

    async def execute(
        self,
        action_name: str,
        inputs: dict[str, Any],
    ) -> dict[str, Any]:
        """Execute an action and return results."""
        ...


class IScopeManager(Protocol):
    """Interface for scope management (dynamic action filtering)."""

    def get_available_actions(
        self,
        state: DialogueState | dict[str, Any],
    ) -> list[str]:
        """Get available actions based on current state."""
        ...

    def get_available_flows(
        self,
        state: DialogueState | dict[str, Any],
    ) -> list[str]:
        """Get available flows based on current state."""
        ...


class INormalizer(Protocol):
    """Interface for value normalization."""

    async def normalize(
        self,
        slot_name: str,
        raw_value: Any,
    ) -> Any:
        """Normalize and validate slot value."""
        ...


class IFlowManager(Protocol):
    """Interface for flow stack management."""

    def push_flow(
        self,
        state: DialogueState,
        flow_name: str,
        inputs: dict[str, Any] | None = None,
        reason: str | None = None,
    ) -> str:
        """Start a new flow instance."""
        ...

    def pop_flow(
        self,
        state: DialogueState,
        outputs: dict[str, Any] | None = None,
        result: str = "completed",
    ) -> None:
        """Finish current flow instance."""
        ...

    def get_active_context(
        self,
        state: DialogueState,
    ) -> FlowContext | None:
        """Get the currently active flow context."""
        ...

    def get_slot(
        self,
        state: DialogueState,
        slot_name: str,
    ) -> Any:
        """Get slot value from active flow."""
        ...

    def set_slot(
        self,
        state: DialogueState,
        slot_name: str,
        value: Any,
    ) -> None:
        """Set slot value in active flow."""
        ...
