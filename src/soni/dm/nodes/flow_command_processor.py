"""Processor for flow-related NLU commands."""

import logging
from typing import Any, cast

from soni.core.commands import Command
from soni.core.types import DialogueState, _merge_flow_slots
from soni.flow.manager import FlowManager, merge_delta

logger = logging.getLogger(__name__)


class FlowCommandProcessor:
    """Processes flow-related commands from NLU.

    Handles StartFlow and CancelFlow commands, updating
    the flow stack appropriately.
    """

    def __init__(self, flow_manager: FlowManager, config: Any) -> None:
        self._fm = flow_manager
        self._config = config

    def process_commands(
        self,
        commands: list[Command],
        state: DialogueState,
    ) -> tuple[list[dict[str, Any]], dict[str, Any]]:
        """Process flow commands and return non-flow commands with updates.

        Args:
            commands: List of NLU commands
            state: Current dialogue state

        Returns:
            Tuple of (remaining_command_dicts, state_updates)
        """
        updates: dict[str, Any] = {}
        remaining_commands: list[dict[str, Any]] = []
        local_state = cast(DialogueState, dict(state))

        for cmd in commands:
            cmd_dict = cmd.model_dump() if hasattr(cmd, "model_dump") else dict(cmd)
            cmd_type = cmd_dict.get("type")

            if cmd_type == "start_flow":
                flow_name = cmd_dict.get("flow_name")
                if isinstance(flow_name, str) and flow_name in self._config.flows:
                    # Check if same flow already active
                    current_ctx = self._fm.get_active_context(local_state)
                    if current_ctx and current_ctx["flow_name"] == flow_name:
                        continue

                    _, delta = self._fm.push_flow(local_state, flow_name)
                    merge_delta(updates, delta)

                    # Update local state for subsequent commands in the same turn
                    if delta.flow_stack is not None:
                        local_state["flow_stack"] = delta.flow_stack
                    if delta.flow_slots is not None:
                        active_slots = local_state.get("flow_slots") or {}
                        local_state["flow_slots"] = _merge_flow_slots(
                            active_slots, delta.flow_slots
                        )
                # ADR-002: Processed here, don't pass to orchestrator

            elif cmd_type == "cancel_flow":
                stack = local_state.get("flow_stack")
                if stack:
                    _, delta = self._fm.pop_flow(local_state)
                    merge_delta(updates, delta)
                    if delta.flow_stack is not None:
                        local_state["flow_stack"] = delta.flow_stack
                # ADR-002: Processed here, don't pass to orchestrator

            else:
                remaining_commands.append(cmd_dict)

        return remaining_commands, updates
