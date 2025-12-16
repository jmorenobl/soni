"""ConfirmNodeFactory - generates confirmation nodes.

Implements full confirmation flow:
1. First visit: Show confirmation prompt, wait for input
2. Subsequent visits: Parse yes/no, set slot, or re-ask if unclear
"""

import logging
from typing import Any

from langchain_core.messages import AIMessage
from langchain_core.runnables import RunnableConfig

from soni.compiler.nodes.base import NodeFunction
from soni.core.config import StepConfig
from soni.core.types import DialogueState

logger = logging.getLogger(__name__)

# Canonical yes/no responses
YES_RESPONSES = frozenset(
    {"yes", "y", "si", "sí", "ok", "okay", "sure", "yep", "yeah", "confirm", "correct"}
)
NO_RESPONSES = frozenset({"no", "n", "nope", "nah", "cancel", "deny", "wrong", "incorrect"})


def _parse_confirmation(user_message: str) -> bool | None:
    """Parse user message to determine yes, no, or unclear.

    Returns:
        True for yes, False for no, None for unclear.
    """
    normalized = user_message.strip().lower()

    if normalized in YES_RESPONSES:
        return True
    if normalized in NO_RESPONSES:
        return False

    # Check for partial matches (e.g., "yes please", "no thanks")
    words = normalized.split()
    if words:
        # Strip punctuation from first word
        first_word = words[0].rstrip(",.!?;:'\"")
        if first_word in YES_RESPONSES:
            return True
        if first_word in NO_RESPONSES:
            return False

    return None


class ConfirmNodeFactory:
    """Factory for confirm step nodes.

    Creates nodes that:
    1. Prompt for confirmation on first visit
    2. Parse yes/no responses on subsequent visits
    3. Re-ask if response is unclear (up to max_retries)
    """

    def create(self, step: StepConfig) -> NodeFunction:
        """Create a node that requests and processes confirmation."""
        if not step.slot:
            raise ValueError(f"Step {step.step} of type 'confirm' missing required field 'slot'")

        slot_name = step.slot
        prompt = step.message or f"Please confirm {slot_name} (yes/no)"
        max_retries = step.max_retries or 3
        retry_key = f"__confirm_retries_{slot_name}"

        async def confirm_node(
            state: DialogueState,
            config: RunnableConfig,
        ) -> dict[str, Any]:
            context = config["configurable"]["runtime_context"]
            flow_manager = context.flow_manager

            # Check if confirmation slot is already filled
            value = flow_manager.get_slot(state, slot_name)
            if value is not None:
                return {"flow_state": "active"}

            # Check if we're waiting for this slot (subsequent visit)
            if state.get("waiting_for_slot") == slot_name:
                user_message = state.get("user_message") or ""
                parsed = _parse_confirmation(user_message)

                if parsed is not None:
                    # Successfully parsed - set slot and continue
                    await flow_manager.set_slot(state, slot_name, parsed)
                    logger.debug(f"Confirmation slot '{slot_name}' set to {parsed}")
                    return {
                        "flow_state": "active",
                        "waiting_for_slot": None,
                        "flow_slots": state["flow_slots"],
                    }

                # Unclear response - check retries
                current_retries = flow_manager.get_slot(state, retry_key) or 0

                if current_retries >= max_retries:
                    # Max retries exceeded - set to False (deny)
                    logger.warning(
                        f"Max retries ({max_retries}) exceeded for confirmation '{slot_name}'"
                    )
                    await flow_manager.set_slot(state, slot_name, False)
                    return {
                        "flow_state": "active",
                        "waiting_for_slot": None,
                        "flow_slots": state["flow_slots"],
                        "last_response": "I didn't understand. Assuming 'no'.",
                        "messages": [AIMessage(content="I didn't understand. Assuming 'no'.")],
                    }

                # Re-ask
                await flow_manager.set_slot(state, retry_key, current_retries + 1)
                retry_prompt = f"I didn't understand. Please answer yes or no: {prompt}"
                return {
                    "flow_state": "waiting_input",
                    "waiting_for_slot": slot_name,
                    "last_response": retry_prompt,
                    "messages": [AIMessage(content=retry_prompt)],
                    "flow_slots": state["flow_slots"],
                }

            # First visit - ask for confirmation
            return {
                "flow_state": "waiting_input",
                "waiting_for_slot": slot_name,
                "messages": [AIMessage(content=prompt)],
                "last_response": prompt,
            }

        confirm_node.__name__ = f"confirm_{step.step}"
        return confirm_node
