"""Flow compiler that translates YAML flow configuration to DAG"""

import logging
from typing import Any

from soni.compiler.dag import DAGEdge, DAGNode, FlowDAG, NodeType
from soni.core.config import SoniConfig

logger = logging.getLogger(__name__)


class FlowCompiler:
    """Compiles YAML flow configuration to intermediate DAG."""

    def __init__(self, config: SoniConfig):
        """
        Initialize FlowCompiler with configuration.

        Args:
            config: Soni configuration containing flows
        """
        self.config = config

    def compile_flow(self, flow_name: str) -> FlowDAG:
        """
        Compile a flow to DAG.

        Args:
            flow_name: Name of the flow to compile

        Returns:
            FlowDAG intermediate representation

        Raises:
            KeyError: If flow_name is not found in config
        """
        if flow_name not in self.config.flows:
            raise KeyError(f"Flow '{flow_name}' not found in configuration")

        flow_config = self.config.flows[flow_name]
        logger.info(f"Compiling flow '{flow_name}' with {len(flow_config.steps)} steps")

        # Extract nodes and edges from steps
        nodes = self._compile_nodes(flow_config)
        edges = self._compile_edges(nodes)

        return FlowDAG(
            name=flow_name,
            nodes=nodes,
            edges=edges,
            entry_point="understand",
        )

    def _compile_nodes(self, flow_config: Any) -> list[DAGNode]:
        """
        Compile flow steps to DAG nodes.

        Args:
            flow_config: Flow configuration

        Returns:
            List of DAG nodes
        """
        # Always start with understand node
        nodes: list[DAGNode] = [DAGNode(id="understand", type=NodeType.UNDERSTAND, config={})]

        # Compile each step to a node
        for step in flow_config.steps:
            node = self._compile_step(step)
            nodes.append(node)

        return nodes

    def _compile_step(self, step: Any) -> DAGNode:
        """
        Compile a single step to DAG node.

        Args:
            step: Step configuration (StepConfig)

        Returns:
            DAG node

        Raises:
            ValueError: If step type is unsupported
        """
        step_type = step.type
        node_id = step.step

        if step_type == "collect":
            if not step.slot:
                raise ValueError(f"Step '{node_id}' of type 'collect' must specify a 'slot'")
            return DAGNode(
                id=node_id,
                type=NodeType.COLLECT,
                config={"slot_name": step.slot},
            )
        elif step_type == "action":
            if not step.call:
                raise ValueError(f"Step '{node_id}' of type 'action' must specify a 'call'")
            return DAGNode(
                id=node_id,
                type=NodeType.ACTION,
                config={
                    "action_name": step.call,
                    "map_outputs": step.map_outputs or {},
                },
            )
        else:
            raise ValueError(f"Unsupported step type: {step_type}")

    def _compile_edges(self, nodes: list[DAGNode]) -> list[DAGEdge]:
        """
        Compile edges connecting nodes sequentially.

        Args:
            nodes: List of DAG nodes

        Returns:
            List of DAG edges
        """
        edges: list[DAGEdge] = []

        if len(nodes) < 2:
            # Only understand node, no edges needed
            return edges

        # Connect nodes sequentially by default
        # START -> understand -> step1 -> step2 -> ... -> END
        # First edge: START -> understand
        edges.append(DAGEdge(source="__start__", target=nodes[0].id))

        # Connect nodes sequentially
        for i in range(len(nodes) - 1):
            edges.append(
                DAGEdge(
                    source=nodes[i].id,
                    target=nodes[i + 1].id,
                )
            )

        # Last edge: last node -> END
        edges.append(DAGEdge(source=nodes[-1].id, target="__end__"))

        return edges
