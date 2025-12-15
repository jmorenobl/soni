"""Dialogue Management for Soni v3.0.

Simplified 4-node architecture:
- understand: NLU → Commands
- execute: Commands → State changes
- step: Run current flow step
- respond: Generate response
"""

from soni.dm.graph import build_graph
from soni.dm.nodes import (
    execute_node,
    respond_node,
    step_node,
    understand_node,
)

__all__ = [
    "build_graph",
    "understand_node",
    "execute_node",
    "step_node",
    "respond_node",
]
