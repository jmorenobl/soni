"""Confirmation handlers - Split from ConfirmNodeFactory for SRP.

Each handler manages a specific aspect of confirmation flow:
- FirstVisitHandler: Initial prompt display
- AffirmHandler: Process affirmation
- DenyHandler: Process denial with optional modification
- ModificationHandler: Handle slot modifications during confirmation
- RetryHandler: Re-ask logic with max retries
"""

import logging
from dataclasses import dataclass
from typing import Any

from langchain_core.messages import AIMessage

from soni.config.patterns import ConfirmationPatternConfig
from soni.core.constants import SlotWaitType
from soni.core.types import DialogueState, FlowManagerProtocol

logger = logging.getLogger(__name__)


@dataclass
class ConfirmationContext:
    """Context for confirmation handlers."""

    slot_name: str
    prompt: str
    retry_key: str
    flow_manager: FlowManagerProtocol
    confirmation_config: ConfirmationPatternConfig | None
    max_retries: int | None


def format_prompt(prompt: str, slots: dict[str, Any]) -> str:
    """Format a prompt template with slot values.

    Safely handles missing keys by returning the original prompt.
    """
    try:
        return prompt.format(**slots)
    except KeyError:
        return prompt


def apply_delta(updates: dict[str, Any], delta: Any) -> None:
    """Helper to merge delta into updates dict.

    Does NOT mutate state - all changes go through updates dict.
    The caller (confirm_node) is responsible for applying updates.
    """
    from soni.flow.manager import merge_delta

    if delta:
        merge_delta(updates, delta)


class FirstVisitHandler:
    """Handles first visit to confirmation node - shows initial prompt."""

    def handle(
        self,
        ctx: ConfirmationContext,
        state: DialogueState,
    ) -> dict[str, Any]:
        """Show initial confirmation prompt."""
        slots = ctx.flow_manager.get_all_slots(state)
        formatted_prompt = format_prompt(ctx.prompt, slots)

        return {
            "flow_state": "waiting_input",
            "waiting_for_slot": ctx.slot_name,
            "waiting_for_slot_type": SlotWaitType.CONFIRMATION,
            "messages": [AIMessage(content=formatted_prompt)],
            "last_response": formatted_prompt,
        }


class AffirmHandler:
    """Handles affirmation - user confirmed."""

    def handle(
        self,
        ctx: ConfirmationContext,
        state: DialogueState,
        updates: dict[str, Any],
    ) -> dict[str, Any]:
        """Process affirmation and proceed (legacy)."""
        delta = ctx.flow_manager.set_slot(state, ctx.slot_name, True)
        apply_delta(updates, delta)
        logger.debug(f"Confirmation slot '{ctx.slot_name}' affirmed")

        updates.update(
            {
                "flow_state": "active",
                "waiting_for_slot": None,
            }
        )
        return updates

    def handle_interrupt(
        self,
        ctx: ConfirmationContext,
        state: DialogueState,
        updates: dict[str, Any],
    ) -> dict[str, Any]:
        """Process affirmation with interrupt() API."""
        delta = ctx.flow_manager.set_slot(state, ctx.slot_name, True)
        apply_delta(updates, delta)
        logger.debug(f"Confirmation slot '{ctx.slot_name}' affirmed")

        # No need to set waiting_for_slot with interrupt()
        updates.update({"flow_state": "active"})
        return updates


class DenyHandler:
    """Handles denial - user denied, optionally with slot to change."""

    def handle(
        self,
        ctx: ConfirmationContext,
        state: DialogueState,
        updates: dict[str, Any],
        commands: list[Any],
        slot_to_change: str | None,
    ) -> dict[str, Any]:
        """Process denial and handle modification requests."""
        # Set confirmation to False
        delta = ctx.flow_manager.set_slot(state, ctx.slot_name, False)
        apply_delta(updates, delta)
        logger.debug(f"Confirmation slot '{ctx.slot_name}' denied")

        # Create working state for subsequent operations in same turn
        working_state = state
        if delta and delta.flow_slots is not None:
            working_state = state.copy()
            working_state["flow_slots"] = delta.flow_slots

        # Check if they also provided a new value via SetSlot
        has_set_slot = any(c.get("type") == "set_slot" for c in commands)

        if has_set_slot:
            # Value already set by SetSlot - re-prompt confirmation
            logger.debug("Denial with SetSlot - re-prompting confirmation")
            delta = ctx.flow_manager.set_slot(state, ctx.slot_name, None)
            apply_delta(updates, delta)

            # Apply delta to working state if needed for get_all_slots
            if delta and delta.flow_slots is not None:
                if working_state is state:
                    working_state = state.copy()
                if "flow_slots" not in working_state:
                    working_state["flow_slots"] = state.get("flow_slots", {}).copy()
                working_state["flow_slots"].update(delta.flow_slots)

            slots = ctx.flow_manager.get_all_slots(working_state)
            formatted_prompt = format_prompt(ctx.prompt, slots)

            updates.update(
                {
                    "flow_state": "waiting_input",
                    "waiting_for_slot": ctx.slot_name,
                    "waiting_for_slot_type": SlotWaitType.CONFIRMATION,
                    "last_response": formatted_prompt,
                    "messages": [AIMessage(content=formatted_prompt)],
                }
            )
            return updates

        if slot_to_change:
            # User wants to change but didn't provide value - ask for it
            logger.debug(f"Modification requested for slot '{slot_to_change}'")
            delta = ctx.flow_manager.set_slot(state, ctx.slot_name, None)
            apply_delta(updates, delta)
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

        # Simple denial - proceed
        updates.update(
            {
                "flow_state": "active",
                "waiting_for_slot": None,
            }
        )
        return updates

    def handle_interrupt(
        self,
        ctx: ConfirmationContext,
        state: DialogueState,
        updates: dict[str, Any],
        commands: list[Any],
        slot_to_change: str | None,
    ) -> dict[str, Any]:
        """Process denial with interrupt() API (no waiting_for_slot)."""
        # Set confirmation to False
        delta = ctx.flow_manager.set_slot(state, ctx.slot_name, False)
        apply_delta(updates, delta)
        logger.debug(f"Confirmation slot '{ctx.slot_name}' denied")

        # Simple denial - just proceed (interrupt handling done by confirm_node)
        updates.update({"flow_state": "active"})
        return updates


class ModificationHandler:
    """Handles slot modifications during confirmation."""

    def handle(
        self,
        ctx: ConfirmationContext,
        state: DialogueState,
        updates: dict[str, Any],
    ) -> dict[str, Any]:
        """Handle slot modification pattern (e.g., 'Let's make it 200')."""
        config = ctx.confirmation_config

        # Default behavior
        behavior = config.modification_handling if config else "update_and_reprompt"
        acknowledgment = config.update_acknowledgment if config else "Updated."

        logger.info(f"Slot modification detected. Behavior: {behavior}")

        if behavior == "update_and_confirm":
            # Auto-confirm after update
            delta = ctx.flow_manager.set_slot(state, ctx.slot_name, True)
            apply_delta(updates, delta)
            updates.update(
                {
                    "flow_state": "active",
                    "waiting_for_slot": None,
                }
            )
            return updates

        # "update_and_reprompt" (Default)
        slots = ctx.flow_manager.get_all_slots(state)
        formatted_prompt = format_prompt(ctx.prompt, slots)
        natural_reprompt = f"{acknowledgment} {formatted_prompt}"

        # Reset retries
        delta = ctx.flow_manager.set_slot(state, ctx.retry_key, 0)
        apply_delta(updates, delta)

        updates.update(
            {
                "flow_state": "waiting_input",
                "waiting_for_slot": ctx.slot_name,
                "waiting_for_slot_type": SlotWaitType.CONFIRMATION,
                "messages": [AIMessage(content=natural_reprompt)],
                "last_response": natural_reprompt,
            }
        )
        return updates

    def handle_interrupt(
        self,
        ctx: ConfirmationContext,
        state: DialogueState,
        updates: dict[str, Any],
    ) -> dict[str, Any]:
        """Handle modification with interrupt() API."""
        config = ctx.confirmation_config

        # Get behavior
        behavior = config.modification_handling if config else "update_and_reprompt"

        logger.info(f"Slot modification detected. Behavior: {behavior}")

        if behavior == "update_and_confirm":
            # Auto-confirm after update
            delta = ctx.flow_manager.set_slot(state, ctx.slot_name, True)
            apply_delta(updates, delta)
            updates.update({"flow_state": "active"})
            return updates

        # "update_and_reprompt" - Reset retries and return
        # Next invocation will call interrupt() with new prompt
        delta = ctx.flow_manager.set_slot(state, ctx.retry_key, 0)
        apply_delta(updates, delta)

        # Don't call interrupt here - let main node do it
        # Just return empty updates to trigger re-execution
        return {}


class RetryHandler:
    """Handles retry logic when NLU doesn't produce affirm/deny."""

    def handle(
        self,
        ctx: ConfirmationContext,
        state: DialogueState,
        updates: dict[str, Any],
    ) -> dict[str, Any]:
        """Handle retry with max retries limit."""
        current_retries = ctx.flow_manager.get_slot(state, ctx.retry_key) or 0

        # Get effective max retries
        config = ctx.confirmation_config
        pattern_max = config.max_retries if config else 3
        effective_max = ctx.max_retries or pattern_max

        if current_retries >= effective_max:
            # Max retries exceeded - default to deny
            logger.warning(
                f"Max retries ({effective_max}) exceeded for confirmation "
                f"'{ctx.slot_name}', defaulting to deny"
            )
            delta = ctx.flow_manager.set_slot(state, ctx.slot_name, False)
            apply_delta(updates, delta)
            updates.update(
                {
                    "flow_state": "active",
                    "waiting_for_slot": None,
                    "last_response": "I didn't understand. Assuming 'no'.",
                    "messages": [AIMessage(content="I didn't understand. Assuming 'no'.")],
                }
            )
            return updates

        # Increment retries
        delta = ctx.flow_manager.set_slot(state, ctx.retry_key, current_retries + 1)
        apply_delta(updates, delta)

        # Update working state for slots
        working_state = state
        if delta and delta.flow_slots is not None:
            working_state = state.copy()
            working_state["flow_slots"] = delta.flow_slots

        # Format prompt with current slot values
        slots = ctx.flow_manager.get_all_slots(working_state)
        formatted_prompt = format_prompt(ctx.prompt, slots)

        # Get retry template from config
        retry_template = (
            config.retry_message if config else "I need a clear yes or no answer. {prompt}"
        )
        retry_prompt = retry_template.format(prompt=formatted_prompt)

        updates.update(
            {
                "flow_state": "waiting_input",
                "waiting_for_slot": ctx.slot_name,
                "waiting_for_slot_type": SlotWaitType.CONFIRMATION,
                "last_response": retry_prompt,
                "messages": [AIMessage(content=retry_prompt)],
            }
        )
        return updates

    def handle_interrupt(
        self,
        ctx: ConfirmationContext,
        state: DialogueState,
        updates: dict[str, Any],
    ) -> dict[str, Any]:
        """Handle max retries with interrupt() API."""
        # Get effective max retries
        config = ctx.confirmation_config
        pattern_max = config.max_retries if config else 3
        effective_max = ctx.max_retries or pattern_max

        # Max retries exceeded - default to deny
        logger.warning(
            f"Max retries ({effective_max}) exceeded for confirmation "
            f"'{ctx.slot_name}', defaulting to deny"
        )
        delta = ctx.flow_manager.set_slot(state, ctx.slot_name, False)
        apply_delta(updates, delta)
        updates.update({"flow_state": "active"})
        return updates
