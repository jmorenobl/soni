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
from soni.core.constants import CommandType, SlotWaitType
from soni.core.types import DialogueState, get_runtime_context
from soni.flow.manager import merge_delta

logger = logging.getLogger(__name__)


def _format_prompt(prompt: str, slots: dict[str, Any]) -> str:
    """Format a prompt template with slot values.

    Safely handles missing keys by returning the original prompt.
    """
    try:
        return prompt.format(**slots)
    except KeyError:
        return prompt


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


def _apply_delta(state: DialogueState, updates: dict[str, Any], delta: Any) -> None:
    """Helper to merge delta and apply to state for subsequent operations."""
    merge_delta(updates, delta)
    if delta and delta.flow_slots is not None:
        state["flow_slots"] = delta.flow_slots


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
        retry_key = f"__confirm_retries_{slot_name}"

        async def confirm_node(
            state: DialogueState,
            config: RunnableConfig,
        ) -> dict[str, Any]:
            context = get_runtime_context(config)
            flow_manager = context.flow_manager

            # Build updates dict for merging deltas
            updates: dict[str, Any] = {}

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
                    delta = flow_manager.set_slot(state, slot_name, is_affirmed)
                    _apply_delta(state, updates, delta)
                    logger.debug(f"Confirmation slot '{slot_name}' set to {is_affirmed} via NLU")

                    if not is_affirmed:
                        # User denied - check if they also provided a new value via SetSlot
                        has_set_slot = any(c.get("type") == "set_slot" for c in commands)

                        if has_set_slot:
                            # Value already set by SetSlot (processed by understand_node)
                            # Just re-prompt confirmation with new values
                            logger.debug("Denial with SetSlot - re-prompting confirmation")
                            delta = flow_manager.set_slot(state, slot_name, None)
                            _apply_delta(state, updates, delta)
                            slots = flow_manager.get_all_slots(state)
                            formatted_prompt = _format_prompt(prompt, slots)

                            updates.update(
                                {
                                    "flow_state": "waiting_input",
                                    "waiting_for_slot": slot_name,
                                    "waiting_for_slot_type": SlotWaitType.CONFIRMATION,
                                    "last_response": formatted_prompt,
                                    "messages": [AIMessage(content=formatted_prompt)],
                                }
                            )
                            return updates

                        elif slot_to_change:
                            # User wants to change but didn't provide value - ask for it
                            logger.debug(f"Modification requested for slot '{slot_to_change}'")
                            delta = flow_manager.set_slot(state, slot_name, None)
                            _apply_delta(state, updates, delta)
                            prompt_message = f"What would you like to change {slot_to_change} to?"
                            updates.update(
                                {
                                    "flow_state": "waiting_input",
                                    "waiting_for_slot": slot_to_change,
                                    "waiting_for_slot_type": SlotWaitType.COLLECTION,
                                    "messages": [AIMessage(content=prompt_message)],
                                    "last_response": prompt_message,
                                }
                            )
                            return updates

                    updates.update(
                        {
                            "flow_state": "active",
                            "waiting_for_slot": None,
                        }
                    )
                    return updates

                # NLU didn't produce affirm/deny - check retries

                # -------------------------------------------------------------
                # NEW: Check for Slot Modification Pattern (e.g., "Let's make it 200")
                # -------------------------------------------------------------
                has_modification = any(c.get("type") == "set_slot" for c in commands)

                if has_modification:
                    # Get behavior config safely (DRY) - used for both modification and retry logic
                    from soni.dm.patterns import get_pattern_config

                    patterns = get_pattern_config(context)
                    confirmation_cfg = patterns.confirmation if patterns else None

                    # Default behavior
                    behavior = (
                        confirmation_cfg.modification_handling
                        if confirmation_cfg
                        else "update_and_reprompt"
                    )
                    acknowledgment = (
                        confirmation_cfg.update_acknowledgment if confirmation_cfg else "Updated."
                    )

                    logger.info(f"Slot modification detected. Behavior: {behavior}")

                    if behavior == "update_and_confirm":
                        delta = flow_manager.set_slot(state, slot_name, True)
                        _apply_delta(state, updates, delta)
                        updates.update(
                            {
                                "flow_state": "active",
                                "waiting_for_slot": None,
                            }
                        )
                        return updates
                    else:
                        # "update_and_reprompt" (Default)
                        slots = flow_manager.get_all_slots(state)
                        formatted_prompt = _format_prompt(prompt, slots)
                        natural_reprompt = f"{acknowledgment} {formatted_prompt}"

                        # Reset retries
                        delta = flow_manager.set_slot(state, retry_key, 0)
                        _apply_delta(state, updates, delta)

                        updates.update(
                            {
                                "flow_state": "waiting_input",
                                "waiting_for_slot": slot_name,
                                "waiting_for_slot_type": SlotWaitType.CONFIRMATION,
                                "messages": [AIMessage(content=natural_reprompt)],
                                "last_response": natural_reprompt,
                            }
                        )
                        return updates

                # -------------------------------------------------------------
                # Standard Retry Logic (Only if no modification occurred)
                # -------------------------------------------------------------
                current_retries = flow_manager.get_slot(state, retry_key) or 0

                # Config already loaded above if has_modification was true,
                # otherwise load it now for retry logic
                if not has_modification:
                    from soni.dm.patterns import get_pattern_config

                    patterns = get_pattern_config(context)
                pattern_max_retries = patterns.confirmation.max_retries if patterns else 3
                effective_max = step.max_retries or pattern_max_retries

                if current_retries >= effective_max:
                    # Max retries exceeded - default to deny
                    logger.warning(
                        f"Max retries ({effective_max}) exceeded for confirmation "
                        f"'{slot_name}', defaulting to deny"
                    )
                    delta = flow_manager.set_slot(state, slot_name, False)
                    _apply_delta(state, updates, delta)
                    updates.update(
                        {
                            "flow_state": "active",
                            "waiting_for_slot": None,
                            "last_response": "I didn't understand. Assuming 'no'.",
                            "messages": [AIMessage(content="I didn't understand. Assuming 'no'.")],
                        }
                    )
                    return updates

                # Re-ask
                delta = flow_manager.set_slot(state, retry_key, current_retries + 1)
                _apply_delta(state, updates, delta)

                # Format prompt with current slot values for retry
                slots = flow_manager.get_all_slots(state)
                formatted_prompt = _format_prompt(prompt, slots)

                # Get retry template from config (DRY)
                retry_template = (
                    patterns.confirmation.retry_message
                    if patterns
                    else "I need a clear yes or no answer. {prompt}"
                )
                retry_prompt = retry_template.format(prompt=formatted_prompt)

                updates.update(
                    {
                        "flow_state": "waiting_input",
                        "waiting_for_slot": slot_name,
                        "waiting_for_slot_type": SlotWaitType.CONFIRMATION,
                        "last_response": retry_prompt,
                        "messages": [AIMessage(content=retry_prompt)],
                    }
                )
                return updates

            # First visit - ask for confirmation
            slots = flow_manager.get_all_slots(state)
            formatted_prompt = _format_prompt(prompt, slots)

            return {
                "flow_state": "waiting_input",
                "waiting_for_slot": slot_name,
                "waiting_for_slot_type": SlotWaitType.CONFIRMATION,
                "messages": [AIMessage(content=formatted_prompt)],
                "last_response": formatted_prompt,
            }

        confirm_node.__name__ = f"confirm_{step.step}"
        return confirm_node
