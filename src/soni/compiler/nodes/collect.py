"""CollectNodeFactory - generates collect step nodes with interrupt() support.

Implements command-based approach:
1. Check if slot already filled (idempotent)
2. Check if NLU provided SetSlot command
3. If no command, use interrupt() to pause and wait
"""

from typing import Any

from langchain_core.messages import AIMessage
from langgraph.runtime import Runtime
from langgraph.types import interrupt

from soni.compiler.nodes.base import NodeFunction
from soni.compiler.nodes.utils import require_field
from soni.config.steps import CollectStepConfig, StepConfig
from soni.core.commands import SetSlot
from soni.core.types import DialogueState, RuntimeContext
from soni.flow.manager import FlowDelta


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

    # Check dict format (for serialized commands)
    if isinstance(cmd, dict):
        return cmd.get("type") == "SetSlot" and cmd.get("slot") == slot_name

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
    """Factory for collect step nodes with command-based interrupt support."""

    def create(
        self,
        step: StepConfig,
        all_steps: list[StepConfig] | None = None,
        step_index: int | None = None,
    ) -> NodeFunction:
        """Create a node that collects a slot value using command-based approach.

        Flow:
        1. Check if slot already filled → skip
        2. Check if NLU provided SetSlot command → use it
        3. Otherwise → interrupt() and wait for input
        """
        if not isinstance(step, CollectStepConfig):
            raise ValueError(f"CollectNodeFactory received wrong step type: {type(step).__name__}")

        slot_name = require_field(step, "slot", str)
        prompt = step.message or f"Please provide {slot_name}"

        async def collect_node(
            state: DialogueState,
            runtime: Runtime[RuntimeContext],
        ) -> dict[str, Any]:
            context = runtime.context
            flow_manager = context.flow_manager

            # 1. Check if slot already has value (idempotent - runs on pause AND resume)
            current_value = flow_manager.get_slot(state, slot_name)
            if current_value is not None:
                return {}  # Already collected, continue

            # 2. COMMAND-BASED: Check if NLU provided value via SetSlot command
            commands = state.get("commands", [])
            for cmd in commands:
                if _is_set_slot_for(cmd, slot_name):
                    # NLU provided value - use it, no interrupt needed!
                    value = cmd.value if isinstance(cmd, SetSlot) else cmd.get("value")
                    delta = flow_manager.set_slot(state, slot_name, value)

                    return _merge_delta(
                        {
                            "waiting_for_slot": None,
                            "waiting_for_slot_type": None,
                        },
                        delta,
                    )

            # 3. No value from NLU - interrupt and wait for input
            # This raises GraphInterrupt on first call
            # Returns resume value on second call (after Command(resume=...))
            user_input = interrupt(
                {
                    "type": "collect",
                    "prompt": prompt,
                    "slot": slot_name,
                }
            )

            # ⚠️ CODE BELOW ONLY RUNS ON RESUME
            # Set slot with direct user input (bypass NLU)
            delta = flow_manager.set_slot(state, slot_name, user_input)

            return _merge_delta(
                {
                    "waiting_for_slot": None,
                    "waiting_for_slot_type": None,
                    "messages": [AIMessage(content=prompt)],
                    "last_response": prompt,
                },
                delta,
            )

        collect_node.__name__ = f"collect_{step.step}"
        return collect_node
