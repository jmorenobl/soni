"""Flow stack management."""

import time
import uuid
from typing import Any

from soni.core.errors import FlowStackError
from soni.core.types import DialogueState, FlowContext


class FlowManager:
    """Manages the flow stack and slot data."""

    def push_flow(
        self,
        state: DialogueState,
        flow_name: str,
        inputs: dict[str, Any] | None = None,
    ) -> str:
        """Push a new flow onto the stack.

        Args:
            state: The dialogue state to modify.
            flow_name: Name of the flow definition to start.
            inputs: Optional initial slot values.

        Returns:
            The flow_id of the new flow.
        """
        flow_id = str(uuid.uuid4())

        context: FlowContext = {
            "flow_id": flow_id,
            "flow_name": flow_name,
            "flow_state": "active",
            "current_step": None,
            "step_index": 0,
            "outputs": {},
            "started_at": time.time(),
        }

        state["flow_stack"].append(context)
        state["flow_slots"][flow_id] = inputs or {}

        return flow_id

    def pop_flow(
        self,
        state: DialogueState,
        result: str = "completed",
    ) -> FlowContext:
        """Pop the top flow from the stack.

        Args:
            state: The dialogue state.
            result: The final state of the flow (e.g., 'completed', 'cancelled').

        Returns:
            The popped FlowContext.

        Raises:
            FlowStackError: If stack is empty.
        """
        if not state["flow_stack"]:
            raise FlowStackError("Cannot pop from empty flow stack")

        context = state["flow_stack"].pop()
        context["flow_state"] = result

        return context

    async def handle_intent_change(
        self,
        state: DialogueState,
        new_flow: str,
    ) -> None:
        """Handle intent switch (push new flow)."""
        self.push_flow(state, new_flow)

    def get_active_context(self, state: DialogueState) -> FlowContext | None:
        """Get the currently active flow context."""
        if not state["flow_stack"]:
            return None
        return state["flow_stack"][-1]

    def set_slot(self, state: DialogueState, slot_name: str, value: Any) -> None:
        """Set a slot value in the active flow context."""
        context = self.get_active_context(state)
        if not context:
            return

        flow_id = context["flow_id"]
        if flow_id not in state["flow_slots"]:
            state["flow_slots"][flow_id] = {}

        state["flow_slots"][flow_id][slot_name] = value

    def get_slot(self, state: DialogueState, slot_name: str) -> Any:
        """Get a slot value from the active flow context."""
        context = self.get_active_context(state)
        if not context:
            return None

        flow_id = context["flow_id"]
        return state["flow_slots"].get(flow_id, {}).get(slot_name)

    def advance_step(self, state: DialogueState) -> bool:
        """Advance to next step in current flow.

        Returns:
            True if advanced, False if no active flow.
        """
        context = self.get_active_context(state)
        if not context:
            return False
        context["step_index"] += 1
        return True

    def get_all_slots(self, state: DialogueState) -> dict[str, Any]:
        """Get all slots for the active flow."""
        context = self.get_active_context(state)
        if context:
            return state["flow_slots"].get(context["flow_id"], {})
        return {}
