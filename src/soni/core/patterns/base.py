"""Base Protocol for Conversation Patterns."""

from typing import Any, Protocol, runtime_checkable

from soni.core.commands import Command
from soni.core.types import DialogueState, RuntimeContext


@runtime_checkable
class ConversationPattern(Protocol):
    """Protocol that all Conversation Patterns must implement.

    A Pattern encapsulates the logic for handling specific conversational behaviors
    (corrections, interruptions, etc.) that cross-cut standard flow logic.
    """

    @property
    def name(self) -> str:
        """Unique name of the pattern."""
        ...

    def matches(self, command: Command, state: DialogueState) -> bool:
        """Check if this pattern handles the given command in the current state."""
        ...

    async def handle(
        self,
        command: Command,
        state: DialogueState,
        context: RuntimeContext,
    ) -> dict[str, Any]:
        """Execute pattern logic and return state updates.

        Args:
            command: The triggering command.
            state: Current dialogue state.
            context: Runtime dependencies (services, config).

        Returns:
            Dictionary of state updates to merge.
        """
        ...
