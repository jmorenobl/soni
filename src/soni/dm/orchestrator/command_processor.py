"""Command processor for orchestrator (SRP)."""

from typing import TYPE_CHECKING, Any, cast

from soni.core.slot_utils import deep_merge_flow_slots
from soni.core.types import DialogueState, FlowDelta, merge_deltas
from soni.dm.orchestrator.commands import CommandHandler

if TYPE_CHECKING:
    from soni.flow.manager import FlowManager


class CommandProcessor:
    """Processes NLU commands and produces FlowDelta."""

    def __init__(self, handlers: list[CommandHandler]) -> None:
        self._handlers = handlers

    async def process(
        self,
        commands: list[dict[str, Any]],
        state: "DialogueState",
        flow_manager: "FlowManager",
    ) -> FlowDelta:
        """Process all commands and return merged delta."""
        # Create a working copy of state to track changes sequentially
        # This ensures that e.g. SetSlot sees the stack created by a preceding StartFlow
        working_state = dict(state)
        working_state["flow_stack"] = list(state.get("flow_stack") or [])
        # Deep copy slots to avoid mutation issues (shallow copy of outer dict might seem enough but better safe)
        working_state["flow_slots"] = {
            k: v.copy() for k, v in (state.get("flow_slots") or {}).items()
        }

        deltas: list[FlowDelta] = []

        for command in commands:
            for handler in self._handlers:
                if handler.can_handle(command):
                    delta = await handler.handle(
                        command, cast("DialogueState", working_state), flow_manager
                    )
                    deltas.append(delta)

                    # Apply delta to working_state for subsequent commands
                    if delta.flow_stack is not None:
                        working_state["flow_stack"] = delta.flow_stack

                    # ... (inside process method)
                    if delta.flow_slots is not None:
                        current_slots = cast(dict[str, dict[str, Any]], working_state["flow_slots"])
                        working_state["flow_slots"] = deep_merge_flow_slots(
                            current_slots, delta.flow_slots
                        )

                    break

        return merge_deltas(deltas) if deltas else FlowDelta()
