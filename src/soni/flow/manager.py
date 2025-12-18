"""Flow stack management.

Immutable-style operations that return state deltas for LangGraph tracking.
All state-mutating methods return dict updates that callers must merge.
"""

import time
import uuid
from dataclasses import dataclass
from typing import Any, cast

from soni.core.errors import FlowStackError
from soni.core.types import DialogueState, FlowContext, FlowContextState


@dataclass
class FlowDelta:
    """State delta returned by FlowManager mutation methods.

    Callers must merge these into their return dict for LangGraph to track.
    """

    flow_stack: list[FlowContext] | None = None
    flow_slots: dict[str, dict[str, Any]] | None = None


class FlowManager:
    """Manages the flow stack and slot data.

    Implements immutable-style operations: methods that would mutate state
    instead return FlowDelta objects containing the new state.

    This ensures LangGraph properly tracks all state changes.
    """

    def push_flow(
        self,
        state: DialogueState,
        flow_name: str,
        inputs: dict[str, Any] | None = None,
    ) -> tuple[str, FlowDelta]:
        """Push a new flow onto the stack.

        Args:
            state: The current dialogue state (not modified).
            flow_name: Name of the flow definition to start.
            inputs: Optional initial slot values.

        Returns:
            Tuple of (flow_id, FlowDelta with updated stack and slots).
        """
        flow_id = str(uuid.uuid4())

        context: FlowContext = {
            "flow_id": flow_id,
            "flow_name": flow_name,
            "flow_state": FlowContextState.ACTIVE,
            "current_step": None,
            "step_index": 0,
            "outputs": {},
            "started_at": time.time(),
        }

        # Create new collections instead of mutating
        new_stack = [*state["flow_stack"], context]
        new_slots = {**state["flow_slots"], flow_id: inputs or {}}

        return flow_id, FlowDelta(flow_stack=new_stack, flow_slots=new_slots)

    def pop_flow(
        self,
        state: DialogueState,
        result: FlowContextState = FlowContextState.COMPLETED,
    ) -> tuple[FlowContext, FlowDelta]:
        """Pop the top flow from the stack.

        Args:
            state: The current dialogue state (not modified).
            result: The final state of the flow.

        Returns:
            Tuple of (popped FlowContext, FlowDelta with updated stack).

        Raises:
            FlowStackError: If stack is empty.
        """
        if not state["flow_stack"]:
            raise FlowStackError("Cannot pop from empty flow stack")

        # Create new stack without last element
        new_stack = list(state["flow_stack"][:-1])

        # Get the popped context and update its state
        popped = cast(FlowContext, dict(state["flow_stack"][-1]))
        popped["flow_state"] = result

        return popped, FlowDelta(flow_stack=new_stack)

    def handle_intent_change(
        self,
        state: DialogueState,
        new_flow: str,
    ) -> FlowDelta | None:
        """Handle intent switch (push new flow, or no-op if same flow active).

        If the same flow is already active on the stack, we skip pushing
        a new instance to preserve existing slot values.

        Args:
            state: The current dialogue state (not modified).
            new_flow: Name of the flow to switch to.

        Returns:
            FlowDelta if a new flow was pushed, None if same flow already active.
        """
        active_ctx = self.get_active_context(state)

        # If the same flow is already active, don't push a duplicate
        if active_ctx and active_ctx["flow_name"] == new_flow:
            return None  # No changes needed

        _, delta = self.push_flow(state, new_flow)
        return delta

    def get_active_context(self, state: DialogueState) -> FlowContext | None:
        """Get the currently active flow context.

        This is a read-only operation, no delta returned.
        """
        if not state["flow_stack"]:
            return None
        return state["flow_stack"][-1]

    def set_slot(self, state: DialogueState, slot_name: str, value: Any) -> FlowDelta | None:
        """Set a slot value in the active flow context.

        Args:
            state: The current dialogue state (not modified).
            slot_name: Name of the slot to set.
            value: Value to set.

        Returns:
            FlowDelta with updated slots, or None if no active flow.
        """
        context = self.get_active_context(state)
        if not context:
            return None

        flow_id = context["flow_id"]
        current_flow_slots = state["flow_slots"].get(flow_id, {})

        # Create new slot dict with update
        new_flow_slots = {**current_flow_slots, slot_name: value}
        new_slots = {**state["flow_slots"], flow_id: new_flow_slots}

        return FlowDelta(flow_slots=new_slots)

    def get_slot(self, state: DialogueState, slot_name: str) -> Any:
        """Get a slot value from the active flow context.

        This is a read-only operation, no delta returned.
        """
        context = self.get_active_context(state)
        if not context:
            return None

        flow_id = context["flow_id"]
        return state["flow_slots"].get(flow_id, {}).get(slot_name)

    def advance_step(self, state: DialogueState) -> FlowDelta | None:
        """Advance to next step in current flow.

        Returns:
            FlowDelta with updated stack, or None if no active flow.
        """
        context = self.get_active_context(state)
        if not context:
            return None

        # Create new context with incremented step
        new_context: FlowContext = {
            **context,
            "step_index": context["step_index"] + 1,
        }

        # Replace the top of the stack
        new_stack = [*state["flow_stack"][:-1], new_context]
        return FlowDelta(flow_stack=new_stack)

    def get_all_slots(self, state: DialogueState) -> dict[str, Any]:
        """Get all slots for the active flow.

        This is a read-only operation, no delta returned.
        """
        context = self.get_active_context(state)
        if context:
            return state["flow_slots"].get(context["flow_id"], {})
        return {}


def merge_delta(updates: dict[str, Any], delta: FlowDelta | None) -> None:
    """Helper to merge a FlowDelta into a node's return dict.

    Args:
        updates: The dict being built by a node for return.
        delta: FlowDelta to merge, or None (no-op).
    """
    if delta is None:
        return

    if delta.flow_stack is not None:
        updates["flow_stack"] = delta.flow_stack
    if delta.flow_slots is not None:
        updates["flow_slots"] = delta.flow_slots
