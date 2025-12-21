"""Flow stack management.

Immutable-style operations that return state deltas for LangGraph tracking.
All state-mutating methods return dict updates that callers must merge.
"""

import logging
import uuid
from typing import Any, cast

from soni.core.errors import FlowStackError
from soni.core.types import DialogueState, FlowContext, FlowContextState, FlowDelta

logger = logging.getLogger(__name__)


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
            "flow_state": FlowContextState.active,
            "current_step": None,
            "step_index": 0,
        }

        # Create new collections instead of mutating
        current_stack = state.get("flow_stack", [])
        if current_stack is None:
            current_stack = []

        new_stack = [*current_stack, context]

        current_slots = state.get("flow_slots", {})
        if current_slots is None:
            current_slots = {}

        new_slots = {**current_slots, flow_id: inputs or {}}

        return flow_id, FlowDelta(flow_stack=new_stack, flow_slots=new_slots)

    def pop_flow(
        self,
        state: DialogueState,
        result: FlowContextState = FlowContextState.completed,
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
        stack = state.get("flow_stack")
        if not stack:
            raise FlowStackError("Cannot pop from empty flow stack")

        # Create new stack without last element
        new_stack = list(stack[:-1])

        popped = cast(FlowContext, dict(stack[-1]))
        popped["flow_state"] = result

        # Cleanup executed steps for the popped flow
        # Use None to signal removal in _merge_dicts reducer
        return popped, FlowDelta(
            flow_stack=new_stack,
            executed_steps={popped["flow_id"]: None},
        )

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
            logger.debug(f"Intent change skipped: flow '{new_flow}' already active")
            return None  # No changes needed

        _, delta = self.push_flow(state, new_flow)
        return delta

    def get_active_flow_id(self, state: DialogueState) -> str | None:
        """Get the ID of the active flow."""
        context = self.get_active_context(state)
        if not context:
            return None
        return context["flow_id"]

    def get_active_context(self, state: DialogueState) -> FlowContext | None:
        """Get the currently active flow context."""
        stack = state.get("flow_stack")
        if not stack:
            return None
        return stack[-1]

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
            logger.debug(f"set_slot('{slot_name}') skipped: no active flow context")
            return None

        flow_id = context["flow_id"]

        # Return minimal delta - let the reducer merge it
        new_slots = {flow_id: {slot_name: value}}

        return FlowDelta(flow_slots=new_slots)

    def get_slot(self, state: DialogueState, slot_name: str) -> Any:
        """Get a slot value from the active flow context."""
        context = self.get_active_context(state)
        if not context:
            logger.debug(f"get_slot('{slot_name}') returning None: no active flow context")
            return None

        flow_id = context["flow_id"]
        # Safe access with get()
        slots = state.get("flow_slots", {})
        if slots is None:
            return None

        return slots.get(flow_id, {}).get(slot_name)

    def advance_step(self, state: DialogueState) -> FlowDelta | None:
        """Advance to next step in current flow.

        Returns:
            FlowDelta with updated stack, or None if no active flow.
        """
        context = self.get_active_context(state)
        if not context:
            logger.debug("advance_step skipped: no active flow context")
            return None

        # Create new context with incremented step
        new_context: FlowContext = {
            **context,
            "step_index": context["step_index"] + 1,
        }

        # Replace the top of the stack
        stack = state.get("flow_stack", [])
        new_stack = [*stack[:-1], new_context]
        return FlowDelta(flow_stack=new_stack)

    def get_all_slots(self, state: DialogueState) -> dict[str, Any]:
        """Get all slots for the active flow."""
        context = self.get_active_context(state)
        if context:
            # Safe access
            slots = state.get("flow_slots", {})
            if slots is None:
                return {}
            return slots.get(context["flow_id"], {})
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
        # Note: We rely on the reducer to merge, so simple assignment to return dict is fine
        # provided we are returning to LangGraph.
        # However, if we are doing local merging in execute_node, we might need manual merge.
        # But for M2 simple case, returning dict is standard.

    if delta.executed_steps is not None:
        updates["_executed_steps"] = delta.executed_steps
