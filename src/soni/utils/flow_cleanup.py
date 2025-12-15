"""Flow cleanup utilities following SRP."""

from typing import Any

from soni.core.types import DialogueState


class FlowCleanupManager:
    """Manage flow cleanup and archiving (single responsibility)."""

    @staticmethod
    def cleanup_completed_flow(state: DialogueState) -> dict[str, Any]:
        """Clean up completed flow from stack and archive.

        Only cleans up if:
        1. Flow stack is not empty
        2. Top flow has flow_state="completed"

        Args:
            state: Current dialogue state

        Returns:
            Partial state updates with cleaned flow_stack and updated metadata,
            or empty dict if no cleanup needed
        """
        flow_stack = state.get("flow_stack", [])
        if not flow_stack:
            return {}

        top_flow = flow_stack[-1]
        if top_flow.get("flow_state") != "completed":
            return {}

        # Pop completed flow
        flow_stack_copy = flow_stack.copy()
        completed_flow = flow_stack_copy.pop()

        # Archive in metadata
        metadata = state.get("metadata", {}).copy()
        if "completed_flows" not in metadata:
            metadata["completed_flows"] = []
        metadata["completed_flows"].append(completed_flow)

        result: dict[str, Any] = {
            "flow_stack": flow_stack_copy,
            "metadata": metadata,
        }

        # Restore parent flow's conversation state if parent exists
        if flow_stack_copy:
            parent_flow = flow_stack_copy[-1]
            parent_step = parent_flow.get("current_step")
            # If parent was waiting for a slot, restore that state
            if parent_step and parent_step.startswith("collect_"):
                slot_name = parent_step.replace("collect_", "")
                result["conversation_state"] = "waiting_for_slot"
                result["waiting_for_slot"] = slot_name
                result["current_prompted_slot"] = slot_name
            elif parent_step and parent_step.startswith("confirm_"):
                result["conversation_state"] = "confirming"
            else:
                result["conversation_state"] = "idle"

        return result

    @staticmethod
    def should_cleanup(state: DialogueState) -> bool:
        """Check if flow cleanup is needed.

        Args:
            state: Current dialogue state

        Returns:
            True if top flow is completed and needs cleanup
        """
        flow_stack = state.get("flow_stack", [])
        if not flow_stack:
            return False
        return flow_stack[-1].get("flow_state") == "completed"
