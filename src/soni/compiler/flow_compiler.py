"""Flow compiler that translates YAML flow configuration to DAG"""

import logging

from soni.compiler.dag import DAGEdge, DAGNode, FlowDAG, NodeType
from soni.compiler.parser import ParsedStep, StepParser
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
        self.parser = StepParser()

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

        # Parse steps first
        parsed_steps = self.parser.parse(flow_config.steps)

        # Extract nodes and edges from parsed steps
        nodes = self._compile_nodes_from_parsed(parsed_steps)
        edges = self._compile_edges(nodes)

        return FlowDAG(
            name=flow_name,
            nodes=nodes,
            edges=edges,
            entry_point="understand",
        )

    def _compile_nodes_from_parsed(self, parsed_steps: list[ParsedStep]) -> list[DAGNode]:
        """
        Compile parsed steps to DAG nodes.

        Args:
            parsed_steps: List of ParsedStep objects

        Returns:
            List of DAG nodes
        """
        # Always start with understand node
        nodes: list[DAGNode] = [DAGNode(id="understand", type=NodeType.UNDERSTAND, config={})]

        # Compile each parsed step to a node
        for parsed in parsed_steps:
            node = self._compile_parsed_step(parsed)
            nodes.append(node)

        return nodes

    def _compile_parsed_step(self, parsed: ParsedStep) -> DAGNode:
        """
        Compile a parsed step to DAG node.

        Args:
            parsed: ParsedStep object

        Returns:
            DAG node

        Raises:
            ValueError: If step type is unsupported
        """
        if parsed.step_type == "collect":
            return DAGNode(
                id=parsed.step_id,
                type=NodeType.COLLECT,
                config={"slot_name": parsed.config["slot_name"]},
            )
        elif parsed.step_type == "action":
            return DAGNode(
                id=parsed.step_id,
                type=NodeType.ACTION,
                config={
                    "action_name": parsed.config["action_name"],
                    "map_outputs": parsed.config.get("map_outputs", {}),
                },
            )
        else:
            raise ValueError(f"Unsupported parsed step type: {parsed.step_type}")

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
