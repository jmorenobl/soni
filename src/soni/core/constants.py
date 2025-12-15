"""Constants and enums for Soni v3.0.

Simplified from v2.0 - only essential states and nodes.
"""

from enum import StrEnum

__all__ = ["FlowState", "NodeName"]


class FlowState(StrEnum):
    """Flow execution states.
    
    Only 3 states needed for the simplified architecture.
    """
    
    RUNNING = "running"
    """Flow is executing, processing commands."""
    
    WAITING_INPUT = "waiting_input"
    """Flow paused, waiting for user input."""
    
    DONE = "done"
    """Flow completed or cancelled."""


class NodeName(StrEnum):
    """Node names in the simplified dialogue graph.
    
    Only 4 nodes in v3.0:
    - understand: NLU → Commands
    - execute: Commands → State changes
    - step: Run current flow step
    - respond: Generate response
    """
    
    UNDERSTAND = "understand"
    """NLU processing, generates Commands from user message."""
    
    EXECUTE = "execute"
    """Execute commands (SetSlot, StartFlow, etc.)."""
    
    STEP = "step"
    """Run the current step in the active flow."""
    
    RESPOND = "respond"
    """Generate response message for user."""
