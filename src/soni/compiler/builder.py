"""Step compiler that generates LangGraph StateGraph from parsed steps"""

import logging
from typing import Any

from langgraph.graph import END, START, StateGraph

from soni.compiler.dag import DAGEdge, DAGNode, FlowDAG, NodeType
from soni.compiler.parser import ParsedStep
from soni.core.config import SoniConfig
from soni.core.errors import CompilationError
from soni.core.interfaces import IActionHandler, INLUProvider, INormalizer, IScopeManager
from soni.core.state import DialogueState, RuntimeContext

logger = logging.getLogger(__name__)


class StepCompiler:
    """Compiles parsed steps to LangGraph StateGraph."""

    def __init__(
        self,
        config: SoniConfig,
        nlu_provider: INLUProvider | None = None,
        normalizer: INormalizer | None = None,
        scope_manager: IScopeManager | None = None,
        action_handler: IActionHandler | None = None,
    ):
        """
        Initialize StepCompiler.

        Args:
            config: Soni configuration
            nlu_provider: NLU provider for understand node
            normalizer: Normalizer for slot normalization
            scope_manager: Scope manager for action scoping
            action_handler: Action handler for executing actions
        """
        self.config = config
        self.nlu_provider = nlu_provider
        self.normalizer = normalizer
        self.scope_manager = scope_manager
        self.action_handler = action_handler

    def compile(
        self,
        flow_name: str,
        parsed_steps: list[ParsedStep],
    ) -> StateGraph[DialogueState]:
        """
        Compile parsed steps to LangGraph StateGraph.

        Args:
            flow_name: Name of the flow being compiled
            parsed_steps: List of parsed steps from StepParser

        Returns:
            Compiled StateGraph ready for execution

        Raises:
            CompilationError: If compilation fails
        """
        logger.info(f"Compiling flow '{flow_name}' with {len(parsed_steps)} steps")

        # Generate DAG from parsed steps
        dag = self._generate_dag(flow_name, parsed_steps)

        # Validate DAG
        self._validate_dag(dag)

        # Build StateGraph from DAG
        graph = self._build_graph(dag)

        return graph

    def _generate_dag(self, flow_name: str, parsed_steps: list[ParsedStep]) -> FlowDAG:
        """Generate DAG from parsed steps."""
        nodes: list[DAGNode] = [DAGNode(id="understand", type=NodeType.UNDERSTAND, config={})]

        # Convert parsed steps to DAG nodes
        for parsed in parsed_steps:
            node = self._parsed_to_dag_node(parsed)
            nodes.append(node)

        # Generate linear edges
        edges = self._generate_linear_edges(nodes)

        return FlowDAG(
            name=flow_name,
            nodes=nodes,
            edges=edges,
            entry_point="understand",
        )

    def _parsed_to_dag_node(self, parsed: ParsedStep) -> DAGNode:
        """Convert ParsedStep to DAGNode."""
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
            raise CompilationError(
                f"Unsupported step type in compilation: {parsed.step_type}",
                step_name=parsed.step_id,
                flow_name="",
            )

    def _generate_linear_edges(self, nodes: list[DAGNode]) -> list[DAGEdge]:
        """Generate linear edges connecting nodes sequentially."""
        edges: list[DAGEdge] = []

        if len(nodes) < 2:
            # Only understand node, no edges needed
            return edges

        # Connect nodes sequentially
        # START -> understand -> step1 -> step2 -> ... -> END
        edges.append(DAGEdge(source="__start__", target=nodes[0].id))

        for i in range(len(nodes) - 1):
            edges.append(
                DAGEdge(
                    source=nodes[i].id,
                    target=nodes[i + 1].id,
                )
            )

        edges.append(DAGEdge(source=nodes[-1].id, target="__end__"))

        return edges

    def _validate_dag(self, dag: FlowDAG) -> None:
        """
        Validate DAG structure.

        Raises:
            CompilationError: If DAG is invalid
        """
        # Check that all nodes have unique IDs
        node_ids = [node.id for node in dag.nodes]
        if len(node_ids) != len(set(node_ids)):
            duplicates = [id for id in node_ids if node_ids.count(id) > 1]
            raise CompilationError(
                f"Duplicate node IDs in flow '{dag.name}': {duplicates}",
                flow_name=dag.name,
            )

        # Check that all edge sources and targets exist
        node_id_set = set(node_ids)
        for edge in dag.edges:
            if edge.source != "__start__" and edge.source not in node_id_set:
                raise CompilationError(
                    f"Edge source '{edge.source}' not found in nodes",
                    flow_name=dag.name,
                )
            if edge.target != "__end__" and edge.target not in node_id_set:
                raise CompilationError(
                    f"Edge target '{edge.target}' not found in nodes",
                    flow_name=dag.name,
                )

        # Check that entry point exists
        if dag.entry_point not in node_id_set:
            raise CompilationError(
                f"Entry point '{dag.entry_point}' not found in nodes",
                flow_name=dag.name,
            )

    def _build_graph(self, dag: FlowDAG) -> StateGraph[DialogueState]:
        """Build LangGraph StateGraph from DAG."""

        # Create runtime context
        context = RuntimeContext(
            config=self.config,
            scope_manager=self.scope_manager or self._create_default_scope_manager(),
            normalizer=self.normalizer or self._create_default_normalizer(),
            action_handler=self.action_handler or self._create_default_action_handler(),
            du=self.nlu_provider or self._create_default_nlu_provider(),
        )

        # Create StateGraph
        graph = StateGraph(DialogueState)

        # Add nodes from DAG
        for node in dag.nodes:
            node_fn = self._create_node_function(node, context)
            graph.add_node(node.id, node_fn)

        # Add edges from DAG (linear only for now)
        for edge in dag.edges:
            if edge.source == "__start__":
                graph.add_edge(START, edge.target)
            elif edge.target == "__end__":
                graph.add_edge(edge.source, END)
            else:
                graph.add_edge(edge.source, edge.target)

        return graph

    def _create_node_function(
        self,
        node: DAGNode,
        context: RuntimeContext,
    ) -> Any:
        """Create node function from DAG node."""
        from soni.dm.nodes import (
            create_action_node_factory,
            create_collect_node_factory,
            create_understand_node,
        )

        if node.type == NodeType.UNDERSTAND:
            return create_understand_node(
                scope_manager=context.scope_manager,
                normalizer=context.normalizer,
                nlu_provider=context.du,
                context=context,
            )
        elif node.type == NodeType.COLLECT:
            return create_collect_node_factory(
                slot_name=node.config["slot_name"],
                context=context,
            )
        elif node.type == NodeType.ACTION:
            return create_action_node_factory(
                action_name=node.config["action_name"],
                context=context,
            )
        else:
            raise CompilationError(
                f"Unsupported node type: {node.type}",
                node_id=node.id,
            )

    def _create_default_scope_manager(self) -> IScopeManager:
        """Create default scope manager."""
        from soni.core.scope import ScopeManager

        return ScopeManager(config=self.config)

    def _create_default_normalizer(self) -> INormalizer:
        """Create default normalizer."""
        from soni.du.normalizer import SlotNormalizer

        return SlotNormalizer(config=self.config)

    def _create_default_action_handler(self) -> IActionHandler:
        """Create default action handler."""
        from soni.actions.base import ActionHandler

        return ActionHandler(config=self.config)

    def _create_default_nlu_provider(self) -> INLUProvider:
        """Create default NLU provider."""
        from soni.du.modules import SoniDU

        scope_manager = self.scope_manager or self._create_default_scope_manager()
        return SoniDU(scope_manager=scope_manager)
