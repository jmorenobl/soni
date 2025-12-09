"""DAG (Directed Acyclic Graph) structures for dialogue flow compilation"""

from dataclasses import dataclass
from enum import Enum
from typing import Any


class NodeType(Enum):
    """Types of nodes in the dialogue graph."""

    UNDERSTAND = "understand"
    COLLECT = "collect"
    ACTION = "action"
    MESSAGE = "message"
    BRANCH = "branch"
    CONFIRM = "confirm"


@dataclass
class DAGNode:
    """Node in the dialogue flow DAG."""

    id: str
    type: NodeType
    config: dict[str, Any]


@dataclass
class DAGEdge:
    """Edge connecting two nodes in the DAG."""

    source: str
    target: str
    condition: str | None = None  # For conditional edges (future)


@dataclass
class FlowDAG:
    """Intermediate DAG representation of a dialogue flow."""

    name: str
    nodes: list[DAGNode]
    edges: list[DAGEdge]
    entry_point: str = "understand"
