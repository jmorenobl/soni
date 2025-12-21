"""CollectNodeFactory - generates collect step nodes.

Implements the LangGraph pattern: interrupt at START of node.

Flow:
1. Check if slot already filled (idempotent)
2. Check if NLU provided SetSlot command (via resume or state)
3. If no value, call interrupt() to get user input
4. On resume, commands come via interrupt() return value

Note: Due to subgraph state isolation, commands must be passed via
interrupt() return value, not state.commands.
"""

from typing import Any

from langgraph.runtime import Runtime
from langgraph.types import Command
from soni.compiler.nodes.base import NodeFunction
from soni.compiler.nodes.utils import require_field
from soni.core.commands import SetSlot
from soni.core.types import DialogueState, RuntimeContext
from soni.flow.manager import FlowDelta

from soni.config.steps import CollectStepConfig, StepConfig


def _is_set_slot_for(cmd: Any, slot_name: str) -> bool:
    """Check if command is SetSlot for specific slot.

    Args:
        cmd: Command object or dict
        slot_name: Slot name to check

    Returns:
        True if command is SetSlot for this slot
    """
    # Check if it's a SetSlot instance
    if isinstance(cmd, SetSlot):
        return cmd.slot == slot_name

    # Check dict format (for serialized commands from NLU)
    # Serialized format uses snake_case: type="set_slot"
    if isinstance(cmd, dict):
        cmd_type = cmd.get("type", "")
        # Support both snake_case (serialized) and CamelCase formats
        is_set_slot = cmd_type in ("set_slot", "SetSlot")
        return is_set_slot and cmd.get("slot") == slot_name

    # Check generic object with attributes
    return getattr(cmd, "type", None) == "SetSlot" and getattr(cmd, "slot", None) == slot_name


def _merge_delta(updates: dict[str, Any], delta: FlowDelta | None) -> dict[str, Any]:
    """Merge FlowDelta into updates dict.

    Args:
        updates: Base updates dict
        delta: FlowDelta to merge (or None)

    Returns:
        Merged updates dict
    """
    if delta is None:
        return updates

    if delta.flow_stack is not None:
        updates["flow_stack"] = delta.flow_stack
    if delta.flow_slots is not None:
        updates["flow_slots"] = delta.flow_slots

    return updates


class CollectNodeFactory:
    """Factory for collect step nodes.

    Creates nodes that:
    1. Check if slot already has value (idempotent)
    2. Check if NLU provided SetSlot command
    3. Call interrupt() if input needed, get commands via resume value
    """

    def create(
        self,
        step: StepConfig,
        all_steps: list[StepConfig] | None = None,
        step_index: int | None = None,
    ) -> NodeFunction:
        """Create a node that collects a slot value.

        Flow:
        1. Check if slot already filled → skip
        2. Check if NLU provided SetSlot command → use it
        3. Otherwise → call interrupt() and get commands via resume
        """
        if not isinstance(step, CollectStepConfig):
            raise ValueError(f"CollectNodeFactory received wrong step type: {type(step).__name__}")

        slot_name = require_field(step, "slot", str)
        prompt = step.message or f"Please provide {slot_name}"

        async def collect_node(
            state: DialogueState,
            runtime: Runtime[RuntimeContext],
        ) -> dict[str, Any] | Command[Any]:
            context = runtime.context
            flow_manager = context.flow_manager

            # 1. IDEMPOTENT: Check if slot already has value
            current_value = flow_manager.get_slot(state, slot_name)
            if current_value is not None:
                return {}  # Already collected, proceed

            # 2. COMMAND-BASED: Check state.commands
            # (passed from execute_node after NLU)
            commands = list(state.get("commands", []))

            # Check for SetSlot command for this slot
            remaining_commands = []
            slot_value = None
            for cmd in commands:
                if _is_set_slot_for(cmd, slot_name):
                    # NLU provided value - use it
                    slot_value = cmd.value if isinstance(cmd, SetSlot) else cmd.get("value")
                else:
                    remaining_commands.append(cmd)

            if slot_value is not None:
                delta = flow_manager.set_slot(state, slot_name, slot_value)
                updates = _merge_delta({}, delta)
                # Clear consumed command by updating commands list
                updates["commands"] = remaining_commands
                # Clear waiting flags since slot is now filled
                updates["waiting_for_slot"] = None
                updates["waiting_for_slot_type"] = None
                return updates

            # 3. NEED INPUT: Return flag to orchestrator
            # The router will see _need_input and route to END
            updates = {
                "_need_input": True,
                "_pending_prompt": {
                    "type": "collect",
                    "slot": slot_name,
                    "prompt": prompt,
                },
                # Determine wait type
                "waiting_for_slot": slot_name,
                "waiting_for_slot_type": "collection",
            }
            return updates

        collect_node.__name__ = f"collect_{step.step}"
        return collect_node
