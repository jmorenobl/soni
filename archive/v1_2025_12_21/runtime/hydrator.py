"""State Hydrator - Prepares state for graph execution.

Extracted from RuntimeLoop to follow Single Responsibility Principle.
Responsible solely for creating and hydrating dialogue state.
"""

from typing import Any, cast

from langchain_core.messages import HumanMessage
from soni.core.state import create_empty_dialogue_state
from soni.core.types import DialogueState


class StateHydrator:
    """Prepares dialogue state for graph execution.

    SRP: Sole responsibility is state preparation (creation or update).
    """

    def prepare_input(
        self,
        message: str,
        current_state: dict[str, Any] | None,
    ) -> DialogueState:
        """Prepare input state for graph execution.

        Args:
            message: User's input message.
            current_state: Existing state from checkpointer, or None for new conversation.

        Returns:
            DialogueState ready for graph invocation.
        """
        if not current_state:
            # Initialize fresh state for new conversation
            init_state = create_empty_dialogue_state()
            init_state["user_message"] = message
            init_state["messages"] = [HumanMessage(content=message)]
            init_state["turn_count"] = 1
            return init_state
        else:
            # Incremental update for existing conversation
            # Only send changed fields - reducer will merge messages
            input_payload: dict[str, Any] = {
                "user_message": message,
                "messages": [HumanMessage(content=message)],
                "turn_count": int(current_state.get("turn_count", 0)) + 1,
            }
            return cast(DialogueState, input_payload)
