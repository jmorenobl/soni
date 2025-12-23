"""ActionNodeFactory for M5 (ADR-002 compliant)."""

import logging
from typing import Any

from langgraph.runtime import Runtime

from soni.config.models import ActionStepConfig, StepConfig
from soni.core.pending_task import inform
from soni.core.types import DialogueState, NodeFunction
from soni.flow.manager import merge_delta
from soni.runtime.context import RuntimeContext

logger = logging.getLogger(__name__)


async def action_node(
    state: DialogueState,
    runtime: Runtime[RuntimeContext],
    config: ActionStepConfig,
) -> dict[str, Any]:
    """Execute action and display result via InformTask."""
    fm = runtime.context.flow_manager
    action_registry = runtime.context.action_registry
    flow_id = fm.get_active_flow_id(state)
    step_id = config.step
    output_mapping = config.map_outputs or {}

    # IDEMPOTENCY CHECK (ADR-002)
    if flow_id:
        executed = (state.get("_executed_steps") or {}).get(flow_id, set())
        if step_id in executed:
            return {"_branch_target": None}

    # Get current slots
    slots = fm.get_all_slots(state)

    # Execute action
    result = await action_registry.execute(config.call, slots)

    # Build updates dict
    updates: dict[str, Any] = {"_branch_target": None}

    # Map outputs to slots
    if isinstance(result, dict):
        for action_key, slot_name in output_mapping.items():
            if action_key in result:
                delta = fm.set_slot(state, slot_name, result[action_key])
                merge_delta(updates, delta)

    # MARK AS EXECUTED (ADR-002)
    if flow_id:
        updates["_executed_steps"] = {flow_id: {step_id}}

    # Return InformTask with the result message
    prompt = ""
    has_message = False

    if hasattr(result, "message"):
        prompt = result.message
        has_message = True
    elif isinstance(result, dict) and "message" in result:
        prompt = result["message"]
        has_message = True
    elif isinstance(result, str) and result:
        # Simple string result IS a message
        prompt = result
        has_message = True
    else:
        # Default to string representation, but only used if forced
        prompt = str(result)

    wait_for_ack = getattr(config, "wait_for_ack", False)
    if wait_for_ack is not True:
        wait_for_ack = False

    # Only inform if explicitly waiting for ack OR if result has a message
    if wait_for_ack or has_message:
        updates["_pending_task"] = inform(
            prompt=prompt,
            wait_for_ack=wait_for_ack,
            metadata={"action": config.call},
        )

    return updates


class ActionNodeFactory:
    """Factory for action step nodes."""

    def create(
        self,
        step: StepConfig,
        all_steps: list[StepConfig] | None = None,
        step_index: int | None = None,
    ) -> NodeFunction:
        """Create an action node function."""
        if not isinstance(step, ActionStepConfig):
            raise ValueError(f"ActionNodeFactory received wrong step type: {type(step).__name__}")

        async def _node(state: DialogueState, runtime: Runtime[RuntimeContext]) -> dict[str, Any]:
            return await action_node(state, runtime, step)

        _node.__name__ = f"action_{step.step}"
        return _node
