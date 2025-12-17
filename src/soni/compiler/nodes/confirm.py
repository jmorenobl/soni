"""ConfirmNodeFactory - generates confirmation nodes.

Implements full confirmation flow using NLU commands:
1. First visit: Show confirmation prompt, wait for input
2. Subsequent visits: Check NLU commands for affirm/deny
3. Re-ask if no clear confirmation command
"""

import logging
from typing import Any

from langchain_core.messages import AIMessage
from langchain_core.runnables import RunnableConfig

from soni.compiler.nodes.base import NodeFunction
from soni.core.config import StepConfig
from soni.core.constants import CommandType
from soni.core.types import DialogueState, get_runtime_context

logger = logging.getLogger(__name__)


def _find_confirmation_command(commands: list[Any]) -> tuple[bool | None, str | None]:
    """Find affirm or deny command in NLU output.

    Args:
        commands: List of command objects or dicts from NLU.

    Returns:
        Tuple of (is_affirmed, slot_to_change).
        - (True, None) for affirm
        - (False, slot_name) for deny with optional slot to change
        - (None, None) if no confirmation command found
    """
    for cmd in commands:
        # Handle both dict and object forms
        if isinstance(cmd, dict):
            cmd_type = cmd.get("type") or cmd.get("command_type")
            slot_to_change = cmd.get("slot_to_change")
        else:
            cmd_type = getattr(cmd, "type", None) or getattr(cmd, "command_type", None)
            slot_to_change = getattr(cmd, "slot_to_change", None)

        if cmd_type == CommandType.AFFIRM:
            return True, None
        if cmd_type == CommandType.DENY:
            return False, slot_to_change

    return None, None


class ConfirmNodeFactory:
    """Factory for confirm step nodes.

    Creates nodes that:
    1. Prompt for confirmation on first visit
    2. Check NLU commands for affirm/deny on subsequent visits
    3. Re-ask if no clear confirmation command (up to max_retries)
    """

    def create(
        self,
        step: StepConfig,
        all_steps: list[StepConfig] | None = None,
        step_index: int | None = None,
    ) -> NodeFunction:
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
            context = get_runtime_context(config)
            flow_manager = context.flow_manager

            # Check if confirmation slot is already filled
            value = flow_manager.get_slot(state, slot_name)
            if value is not None:
                return {"flow_state": "active"}

            # Check if we're waiting for this slot (subsequent visit)
            if state.get("waiting_for_slot") == slot_name:
                # Get NLU commands from state
                commands = state.get("commands", [])
                is_affirmed, slot_to_change = _find_confirmation_command(commands)

                if is_affirmed is not None:
                    # NLU understood the confirmation
                    await flow_manager.set_slot(state, slot_name, is_affirmed)
                    logger.debug(f"Confirmation slot '{slot_name}' set to {is_affirmed} via NLU")

                    # If denied with slot_to_change, wait for new value
                    if not is_affirmed and slot_to_change:
                        logger.debug(f"Modification requested for slot '{slot_to_change}'")
                        # Clear the confirmation slot so we re-confirm after modification
                        await flow_manager.set_slot(state, slot_name, None)
                        # Prompt for the new value
                        prompt_message = f"What would you like to change {slot_to_change} to?"
                        return {
                            "flow_state": "waiting_input",
                            "waiting_for_slot": slot_to_change,
                            "messages": [AIMessage(content=prompt_message)],
                            "last_response": prompt_message,
                            "flow_slots": state["flow_slots"],
                        }

                    result: dict[str, Any] = {
                        "flow_state": "active",
                        "waiting_for_slot": None,
                        "flow_slots": state["flow_slots"],
                    }

                    return result

                # NLU didn't produce affirm/deny - check retries
                current_retries = flow_manager.get_slot(state, retry_key) or 0

                if current_retries >= max_retries:
                    # Max retries exceeded - default to deny
                    logger.warning(
                        f"Max retries ({max_retries}) exceeded for confirmation "
                        f"'{slot_name}', defaulting to deny"
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
                retry_prompt = f"I need a clear yes or no answer. {prompt}"
                return {
                    "flow_state": "waiting_input",
                    "waiting_for_slot": slot_name,
                    "last_response": retry_prompt,
                    "messages": [AIMessage(content=retry_prompt)],
                    "flow_slots": state["flow_slots"],
                }

            # First visit - ask for confirmation
            slots = flow_manager.get_all_slots(state)
            try:
                formatted_prompt = prompt.format(**slots)
            except KeyError:
                formatted_prompt = prompt

            return {
                "flow_state": "waiting_input",
                "waiting_for_slot": slot_name,
                "messages": [AIMessage(content=formatted_prompt)],
                "last_response": formatted_prompt,
            }

        confirm_node.__name__ = f"confirm_{step.step}"
        return confirm_node
