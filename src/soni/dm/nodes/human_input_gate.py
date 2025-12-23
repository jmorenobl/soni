"""Human Input Gate node - single entry point for user communication."""

from typing import Any

from langgraph.types import interrupt

from soni.core.types import DialogueState


async def human_input_gate(state: DialogueState) -> dict[str, Any]:
    """Single entry point for all user communication.

    This is a pure node - no external dependencies needed.

    Responsibilities:
    1. Receive new user messages
    2. Handle resume from interrupts
    3. Process pending tasks from orchestrator
    """
    # Check if resuming from interrupt
    pending = state.get("_pending_task")
    if pending:
        # Collect user response for pending task
        # interrupt(pending) suspends execution and returns resume value
        resume_value = interrupt(pending)

        # Ensure return is serializable and follows state schema
        return {
            "user_message": str(resume_value),
            "_pending_task": None,
        }

    # Normal message reception:
    # If we are here and not resuming, user_message is already set by loop.ainvoke
    return {}
