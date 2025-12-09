"""Core interfaces (Protocols) for Soni Framework following SOLID principles."""

from typing import TYPE_CHECKING, Any, Protocol, TypeAlias

from soni.core.types import DialogueState as DialogueStateTypedDict
from soni.core.types import FlowContext

if TYPE_CHECKING:
    from soni.core.state import DialogueState as DialogueStateDataclass

    DialogueState: TypeAlias = DialogueStateTypedDict | DialogueStateDataclass | dict[str, Any]
else:
    # Runtime: use TypedDict version for Protocol compatibility
    # The actual implementation will handle both types
    DialogueState: TypeAlias = DialogueStateTypedDict | dict[str, Any]


class INLUProvider(Protocol):
    """Interface for NLU providers.

    The main method is predict() which uses structured types.
    understand() is provided for compatibility with dict-based interfaces.
    """

    async def predict(
        self,
        user_message: str,
        history: Any,  # dspy.History
        context: Any,  # DialogueContext
    ) -> Any:
        """Predict NLU result using structured types (main method).

        This is the primary method used by nodes (e.g., understand_node).
        Uses structured types (dspy.History, DialogueContext) for type safety.

        Args:
            user_message: User's input message
            history: Conversation history (dspy.History)
            context: Dialogue context (DialogueContext)

        Returns:
            NLUOutput (or dict if implementation returns serialized)
        """
        ...

    async def understand(
        self,
        user_message: str,
        dialogue_context: dict[str, Any],
    ) -> dict[str, Any]:
        """Understand user message and return NLU result (dict-based interface).

        This method is provided for compatibility with dict-based interfaces.
        Implementations should convert dict → structured types and call predict().

        Args:
            user_message: User's input message
            dialogue_context: Dict with current_slots, available_actions, etc.

        Returns:
            Dict with message_type, command, slots, and confidence
        """
        ...


class IActionHandler(Protocol):
    """Interface for action execution."""

    async def execute(
        self,
        action_name: str,
        inputs: dict[str, Any] | None = None,
        slots: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Execute an action and return results.

        Args:
            action_name: Name of the action to execute
            inputs: Action inputs (legacy parameter)
            slots: Slot values (preferred parameter)

        Returns:
            Action execution results
        """
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
    ) -> dict[str, str]:
        """Get available flows with descriptions based on current state."""
        ...

    def get_expected_slots(
        self,
        flow_name: str,
        available_actions: list[str],
    ) -> list[str]:
        """Get expected slot names for a flow.

        Args:
            flow_name: Name of the flow
            available_actions: List of available actions in current scope

        Returns:
            List of expected slot names
        """
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
