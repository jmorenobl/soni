"""Flow stack management for Soni Framework."""

import time
import uuid
from typing import Any

from soni.core.errors import FlowStackLimitError
from soni.core.types import DialogueState, FlowContext, FlowState


class FlowManager:
    """Manages flow stack operations and flow instance data."""

    def __init__(self, max_stack_depth: int = 10) -> None:
        """Initialize FlowManager with optional stack depth limit.

        Args:
            max_stack_depth: Maximum depth of flow stack (default: 10)
        """
        self.max_stack_depth = max_stack_depth

    def push_flow(
        self,
        state: DialogueState,
        flow_name: str,
        inputs: dict[str, Any] | None = None,
        reason: str | None = None,
    ) -> str:
        """Start a new flow instance.

        Args:
            state: Dialogue state to modify
            flow_name: Name of the flow to start
            inputs: Optional input values for the flow
            reason: Optional reason for starting the flow

        Returns:
            flow_id: Unique identifier for the new flow instance

        Raises:
            FlowStackLimitError: If stack depth limit is exceeded
        """
        # Check stack depth limit
        if len(state["flow_stack"]) >= self.max_stack_depth:
            raise FlowStackLimitError(
                f"Flow stack depth limit ({self.max_stack_depth}) exceeded",
                current_depth=len(state["flow_stack"]),
                flow_name=flow_name,
            )

        # Pause current flow if exists
        if state["flow_stack"]:
            current = state["flow_stack"][-1]
            current["flow_state"] = "paused"
            current["paused_at"] = time.time()
            current["context"] = reason

        # Create new flow context
        flow_id = f"{flow_name}_{uuid.uuid4().hex[:8]}"
        new_context: FlowContext = {
            "flow_id": flow_id,
            "flow_name": flow_name,
            "flow_state": "active",
            "current_step": None,
            "outputs": {},
            "started_at": time.time(),
            "paused_at": None,
            "completed_at": None,
            "context": None,
        }

        # Add to stack
        state["flow_stack"].append(new_context)

        # Initialize flow_slots with inputs
        state["flow_slots"][flow_id] = inputs.copy() if inputs else {}

        return flow_id

    def pop_flow(
        self,
        state: DialogueState,
        outputs: dict[str, Any] | None = None,
        result: FlowState = "completed",
    ) -> None:
        """Finish current flow instance.

        Args:
            state: Dialogue state to modify
            outputs: Optional output values from the flow
            result: Flow result state (default: "completed")
        """
        if not state["flow_stack"]:
            return

        # Get current flow
        current = state["flow_stack"].pop()

        # Update flow state
        current["flow_state"] = result
        current["completed_at"] = time.time()
        current["outputs"] = outputs or {}

        # Archive completed flow
        if "completed_flows" not in state["metadata"]:
            state["metadata"]["completed_flows"] = []
        state["metadata"]["completed_flows"].append(current)

        # Prune flow_slots (remove data for completed flow)
        flow_id = current["flow_id"]
        if flow_id in state["flow_slots"]:
            del state["flow_slots"][flow_id]

        # Resume previous flow if exists
        if state["flow_stack"]:
            previous = state["flow_stack"][-1]
            previous["flow_state"] = "active"
            previous["paused_at"] = None
            previous["context"] = None

    def get_active_context(
        self,
        state: DialogueState,
    ) -> FlowContext | None:
        """Get the currently active flow context.

        Args:
            state: Dialogue state

        Returns:
            Active flow context or None if no active flow
        """
        if not state["flow_stack"]:
            return None
        return state["flow_stack"][-1]

    def get_slot(
        self,
        state: DialogueState,
        slot_name: str,
    ) -> Any:
        """Get slot value from active flow.

        Args:
            state: Dialogue state
            slot_name: Name of the slot to get

        Returns:
            Slot value or None if not found
        """
        context = self.get_active_context(state)
        if not context:
            return None

        flow_id = context["flow_id"]
        if flow_id not in state["flow_slots"]:
            return None

        return state["flow_slots"][flow_id].get(slot_name)

    def set_slot(
        self,
        state: DialogueState,
        slot_name: str,
        value: Any,
    ) -> None:
        """Set slot value in active flow.

        Args:
            state: Dialogue state to modify
            slot_name: Name of the slot to set
            value: Value to set

        Raises:
            ValueError: If no active flow exists
        """
        context = self.get_active_context(state)
        if not context:
            raise ValueError("No active flow to set slot in")

        flow_id = context["flow_id"]
        if flow_id not in state["flow_slots"]:
            state["flow_slots"][flow_id] = {}

        state["flow_slots"][flow_id][slot_name] = value

    def prune_state(
        self,
        state: DialogueState,
        max_completed_flows: int = 50,
    ) -> None:
        """Prune old completed flows from metadata to manage memory.

        Args:
            state: Dialogue state to prune
            max_completed_flows: Maximum number of completed flows to keep
        """
        if "completed_flows" not in state["metadata"]:
            return

        completed = state["metadata"]["completed_flows"]
        if len(completed) > max_completed_flows:
            # Keep most recent flows
            state["metadata"]["completed_flows"] = completed[-max_completed_flows:]
