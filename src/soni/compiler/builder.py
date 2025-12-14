"""Step compiler that generates LangGraph StateGraph from parsed steps"""

import logging
from typing import Any

from langgraph.graph import END, START, StateGraph

from soni.compiler.dag import DAGEdge, DAGNode, FlowDAG, NodeType
from soni.compiler.parser import ParsedStep
from soni.core.config import SoniConfig
from soni.core.errors import CompilationError
from soni.core.interfaces import IActionHandler, INLUProvider, INormalizer, IScopeManager
from soni.core.state import DialogueState, RuntimeContext, create_runtime_context

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

        # Generate edges with branches and jumps
        edges = self._generate_edges_with_branches(nodes, parsed_steps)

        return FlowDAG(
            name=flow_name,
            nodes=nodes,
            edges=edges,
            entry_point="understand",
        )

    def _parsed_to_dag_node(self, parsed: ParsedStep) -> DAGNode:
        """Convert ParsedStep to DAGNode."""
        if parsed.step_type == "collect":
            config: dict[str, Any] = {"slot_name": parsed.config["slot_name"]}
            if "jump_to" in parsed.config:
                config["jump_to"] = parsed.config["jump_to"]
            return DAGNode(
                id=parsed.step_id,
                type=NodeType.COLLECT,
                config=config,
            )
        elif parsed.step_type == "action":
            config = {
                "action_name": parsed.config["action_name"],
                "map_outputs": parsed.config.get("map_outputs", {}),
            }
            if "jump_to" in parsed.config:
                config["jump_to"] = parsed.config["jump_to"]
            return DAGNode(
                id=parsed.step_id,
                type=NodeType.ACTION,
                config=config,
            )
        elif parsed.step_type == "branch":
            return DAGNode(
                id=parsed.step_id,
                type=NodeType.BRANCH,
                config={
                    "input": parsed.config["input"],
                    "cases": parsed.config["cases"],
                },
            )
        elif parsed.step_type == "confirm":
            config = {}
            if "message" in parsed.config:
                config["message"] = parsed.config["message"]
            if "jump_to" in parsed.config:
                config["jump_to"] = parsed.config["jump_to"]
            return DAGNode(
                id=parsed.step_id,
                type=NodeType.CONFIRM,
                config=config,
            )
        else:
            raise CompilationError(
                f"Unsupported step type in compilation: {parsed.step_type}",
                step_name=parsed.step_id,
                flow_name="",
            )

    def _generate_edges_with_branches(
        self, nodes: list[DAGNode], parsed_steps: list[ParsedStep]
    ) -> list[DAGEdge]:
        """
        Generate edges with support for branches and jumps.

        Args:
            nodes: List of DAG nodes (including understand node)
            parsed_steps: List of parsed steps (for accessing jump_to and branch info)

        Returns:
            List of DAG edges
        """
        edges: list[DAGEdge] = []

        if len(nodes) < 2:
            # Only understand node, no edges needed
            return edges

        # Map step_id to node index (skip understand node at index 0)
        step_id_to_index: dict[str, int] = {}
        for i, parsed in enumerate(parsed_steps):
            # Node index is i+1 because nodes[0] is "understand"
            step_id_to_index[parsed.step_id] = i + 1

        # Connect START to understand node
        edges.append(DAGEdge(source="__start__", target=nodes[0].id))

        # Connect understand to first step (if exists)
        if len(parsed_steps) > 0:
            first_step_node_id = nodes[1].id  # First step is at index 1
            edges.append(DAGEdge(source=nodes[0].id, target=first_step_node_id))

        # Process each step to generate edges
        for i, parsed in enumerate(parsed_steps):
            node_index = i + 1  # +1 because nodes[0] is "understand"
            current_node_id = nodes[node_index].id

            # Check if step has jump_to (explicit jump breaks sequentiality)
            if "jump_to" in parsed.config:
                jump_target = parsed.config["jump_to"]
                # Resolve target: could be step_id or special value
                if jump_target in step_id_to_index:
                    target_node_id = nodes[step_id_to_index[jump_target]].id
                    edges.append(DAGEdge(source=current_node_id, target=target_node_id))
                else:
                    # Could be special target like "__end__" or invalid
                    if jump_target == "__end__":
                        edges.append(DAGEdge(source=current_node_id, target="__end__"))
                    else:
                        # Will be validated later, but create edge anyway
                        # Target might be in a different flow or invalid
                        logger.warning(
                            f"Jump target '{jump_target}' not found in current flow steps"
                        )
                        # Still create edge - validation will catch it
                        edges.append(DAGEdge(source=current_node_id, target=jump_target))
                # Don't create sequential edge if jump_to exists
                continue

            # Check if step is a branch (handled separately with conditional edges)
            if parsed.step_type == "branch":
                # Branch steps create conditional edges, not regular edges
                # Branches route conditionally, so no sequential edge needed
                # But we need to connect previous step to this branch
                # (This is already handled by the sequential logic below for previous step)
                continue

            # Default: sequential connection to next step
            # But skip if next step is a branch (branches handle their own connections)
            if node_index < len(nodes) - 1:
                next_node = nodes[node_index + 1]
                # Check if next node is a branch - if so, connect to it
                # (Branches will handle routing via conditional edges)
                if next_node.type == NodeType.BRANCH:
                    edges.append(DAGEdge(source=current_node_id, target=next_node.id))
                else:
                    # Regular sequential connection
                    edges.append(DAGEdge(source=current_node_id, target=next_node.id))
            else:
                # Last step, connect to END (if not a branch)
                edges.append(DAGEdge(source=current_node_id, target="__end__"))

        return edges

    def _validate_dag(self, dag: FlowDAG) -> None:
        """
        Validate DAG structure.

        Validates:
        - Unique node IDs
        - All edge sources and targets exist
        - Entry point exists
        - All jump_to targets exist
        - All branch case targets exist
        - No cycles in the graph
        - All nodes are reachable from entry point

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

        # Validate jump_to targets and branch case targets
        invalid_targets = self._validate_targets(dag)
        if invalid_targets:
            targets_str = ", ".join(f"'{t}'" for t in invalid_targets)
            raise CompilationError(
                f"Invalid targets in flow '{dag.name}': {targets_str}",
                flow_name=dag.name,
            )

        # Detect cycles
        cycles = self._detect_cycles(dag)
        if cycles:
            cycles_str = " -> ".join(cycles[0]) if cycles else "unknown"
            raise CompilationError(
                f"Cycle detected in flow '{dag.name}': {cycles_str}",
                flow_name=dag.name,
            )

        # Validate reachability (all nodes reachable from entry point)
        unreachable = self._find_unreachable_nodes(dag)
        if unreachable:
            unreachable_str = ", ".join(f"'{n}'" for n in unreachable)
            raise CompilationError(
                f"Unreachable nodes in flow '{dag.name}': {unreachable_str}",
                flow_name=dag.name,
            )

        # Validate map_outputs for action nodes
        self._validate_map_outputs(dag)

    def _validate_targets(self, dag: FlowDAG) -> list[str]:
        """
        Validate that all jump_to and branch case targets exist.

        Args:
            dag: FlowDAG to validate

        Returns:
            List of invalid target names
        """
        node_id_set = {node.id for node in dag.nodes}
        invalid_targets: list[str] = []

        # Check jump_to targets in node configs
        for node in dag.nodes:
            if "jump_to" in node.config:
                jump_target = node.config["jump_to"]
                if jump_target not in node_id_set and jump_target != "__end__":
                    if jump_target not in invalid_targets:
                        invalid_targets.append(jump_target)

        # Check jump_to targets in edges (stored in edge targets)
        for edge in dag.edges:
            if edge.target not in node_id_set and edge.target != "__end__":
                if edge.target not in invalid_targets:
                    invalid_targets.append(edge.target)

        # Check branch case targets
        for node in dag.nodes:
            if node.type == NodeType.BRANCH:
                cases = node.config.get("cases", {})
                for _case_value, target in cases.items():
                    # Resolve target (could be "continue", "jump_to_<step>", or direct name)
                    resolved_target = target
                    if target.startswith("jump_to_"):
                        resolved_target = target.replace("jump_to_", "", 1)
                    elif target == "continue":
                        # "continue" is valid, skip
                        continue

                    # Check if resolved target exists
                    if resolved_target not in node_id_set and resolved_target != "__end__":
                        if resolved_target not in invalid_targets:
                            invalid_targets.append(resolved_target)

        return invalid_targets

    def _detect_cycles(self, dag: FlowDAG) -> list[list[str]]:
        """
        Detect cycles in the DAG using DFS.

        Args:
            dag: FlowDAG to check for cycles

        Returns:
            List of cycles found (each cycle is a list of node IDs)
        """
        # Build adjacency list (excluding START and END)
        adjacency: dict[str, list[str]] = {node.id: [] for node in dag.nodes}

        for edge in dag.edges:
            if edge.source != "__start__" and edge.target != "__end__":
                if edge.source in adjacency:
                    adjacency[edge.source].append(edge.target)

        # DFS to detect cycles
        visited: set[str] = set()
        rec_stack: set[str] = set()
        cycles: list[list[str]] = []
        path: list[str] = []

        def dfs(node_id: str) -> None:
            """DFS helper to detect cycles."""
            visited.add(node_id)
            rec_stack.add(node_id)
            path.append(node_id)

            for neighbor in adjacency.get(node_id, []):
                if neighbor not in visited:
                    dfs(neighbor)
                elif neighbor in rec_stack:
                    # Cycle detected - find the cycle path
                    cycle_start = path.index(neighbor)
                    cycle = path[cycle_start:] + [neighbor]
                    cycles.append(cycle)

            rec_stack.remove(node_id)
            path.pop()

        # Check all nodes
        for node_id in adjacency:
            if node_id not in visited:
                dfs(node_id)

        return cycles

    def _find_unreachable_nodes(self, dag: FlowDAG) -> list[str]:
        """
        Find nodes that are not reachable from the entry point.

        Args:
            dag: FlowDAG to check

        Returns:
            List of unreachable node IDs
        """
        # Build adjacency list (including START -> entry_point)
        adjacency: dict[str, list[str]] = {node.id: [] for node in dag.nodes}
        adjacency["__start__"] = [dag.entry_point]

        for edge in dag.edges:
            if edge.source in adjacency:
                adjacency[edge.source].append(edge.target)

        # Add conditional edges from branches (all case targets are potentially reachable)
        for node in dag.nodes:
            if node.type == NodeType.BRANCH:
                cases = node.config.get("cases", {})
                for target in cases.values():
                    # Resolve target
                    resolved_target = target
                    if target.startswith("jump_to_"):
                        resolved_target = target.replace("jump_to_", "", 1)
                    elif target == "continue":
                        # Continue to next sequential node
                        current_idx = next(
                            (i for i, n in enumerate(dag.nodes) if n.id == node.id), None
                        )
                        if current_idx is not None and current_idx + 1 < len(dag.nodes):
                            resolved_target = dag.nodes[current_idx + 1].id
                        else:
                            resolved_target = "__end__"
                    else:
                        # Direct node ID
                        resolved_target = target

                    # Add to adjacency (branch can reach this target)
                    if node.id in adjacency:
                        if resolved_target not in adjacency[node.id]:
                            adjacency[node.id].append(resolved_target)

        # BFS from START to find all reachable nodes
        reachable: set[str] = set()
        queue: list[str] = ["__start__"]

        while queue:
            current = queue.pop(0)
            if current in reachable:
                continue
            reachable.add(current)

            for neighbor in adjacency.get(current, []):
                if neighbor not in reachable and neighbor != "__end__":
                    queue.append(neighbor)

        # Find unreachable nodes
        all_node_ids = {node.id for node in dag.nodes}
        unreachable = all_node_ids - reachable

        return list(unreachable)

    def _validate_map_outputs(self, dag: FlowDAG) -> None:
        """
        Validate that map_outputs references valid action outputs.

        Args:
            dag: FlowDAG to validate

        Raises:
            CompilationError: If map_outputs references invalid action outputs
        """
        for node in dag.nodes:
            if node.type == NodeType.ACTION:
                action_name = node.config.get("action_name")
                map_outputs = node.config.get("map_outputs")

                if not action_name:
                    continue

                if not map_outputs:
                    continue

                if not isinstance(map_outputs, dict):
                    raise CompilationError(
                        f"map_outputs must be a dict for action '{action_name}', got {type(map_outputs)}",
                        flow_name=dag.name,
                    )

                # Get action config
                if action_name not in self.config.actions:
                    # Action not found - will be caught by other validation
                    continue

                action_config = self.config.actions[action_name]

                # Check that all mapped action fields exist in action outputs
                invalid_fields = []
                for state_var, action_field in map_outputs.items():
                    if action_field not in action_config.outputs:
                        invalid_fields.append(f"{action_field} (mapped to {state_var})")

                if invalid_fields:
                    raise CompilationError(
                        f"Action '{action_name}' map_outputs references invalid output fields: {', '.join(invalid_fields)}. "
                        f"Available outputs: {', '.join(action_config.outputs)}",
                        flow_name=dag.name,
                    )

    def _build_graph(self, dag: FlowDAG) -> StateGraph[DialogueState]:
        """Build LangGraph StateGraph from DAG."""

        # Create runtime context
        context = create_runtime_context(
            config=self.config,
            scope_manager=self.scope_manager or self._create_default_scope_manager(),
            normalizer=self.normalizer or self._create_default_normalizer(),
            action_handler=self.action_handler or self._create_default_action_handler(),
            du=self.nlu_provider or self._create_default_nlu_provider(),
        )

        # Create StateGraph
        graph = StateGraph(DialogueState)

        # Map node IDs to their indices for resolving "continue" targets
        node_id_to_index: dict[str, int] = {node.id: i for i, node in enumerate(dag.nodes)}

        # Add nodes from DAG
        branch_nodes: list[tuple[str, dict[str, Any]]] = []  # (node_id, branch_config)
        for node in dag.nodes:
            node_fn = self._create_node_function(node, context)
            graph.add_node(node.id, node_fn)

            # Track branch nodes for conditional edges
            if node.type == NodeType.BRANCH:
                branch_nodes.append((node.id, node.config))

        # Add regular edges from DAG
        for edge in dag.edges:
            if edge.source == "__start__":
                graph.add_edge(START, edge.target)
            elif edge.target == "__end__":
                graph.add_edge(edge.source, END)
            else:
                graph.add_edge(edge.source, edge.target)

        # Add conditional edges for branch nodes
        for branch_node_id, branch_config in branch_nodes:
            input_var = branch_config["input"]
            cases = branch_config["cases"]

            # Resolve case targets: "continue" -> next step, "jump_to_<step>" -> step, direct name -> step
            resolved_cases: dict[str, str] = {}
            for case_value, target in cases.items():
                if target == "continue":
                    # Find next step after branch node
                    branch_index = node_id_to_index.get(branch_node_id)
                    if branch_index is not None and branch_index + 1 < len(dag.nodes):
                        next_node_id = dag.nodes[branch_index + 1].id
                        resolved_cases[case_value] = next_node_id
                    else:
                        # Last node, route to END
                        resolved_cases[case_value] = END
                elif target.startswith("jump_to_"):
                    # Format: "jump_to_<step_id>"
                    step_id = target.replace("jump_to_", "", 1)
                    # Find node with this step_id
                    target_node_id = None
                    for node in dag.nodes:
                        if node.id == step_id:
                            target_node_id = step_id
                            break
                    if target_node_id:
                        resolved_cases[case_value] = target_node_id
                    else:
                        raise CompilationError(
                            f"Branch case target '{target}' references non-existent step '{step_id}'",
                            step_name=branch_node_id,
                            flow_name=dag.name,
                        )
                else:
                    # Direct step name
                    target_node_id = None
                    for node in dag.nodes:
                        if node.id == target:
                            target_node_id = target
                            break
                    if target_node_id:
                        resolved_cases[case_value] = target_node_id
                    else:
                        raise CompilationError(
                            f"Branch case target '{target}' references non-existent step",
                            step_name=branch_node_id,
                            flow_name=dag.name,
                        )

            # Create router function
            from soni.dm.routing import create_branch_router

            router = create_branch_router(input_var, resolved_cases)

            # Add conditional edge
            # resolved_cases is dict[str, str] which is compatible with dict[Hashable, str]
            from collections.abc import Hashable
            from typing import cast

            graph.add_conditional_edges(
                branch_node_id, router, cast(dict[Hashable, str], resolved_cases)
            )

        return graph

    def _create_node_function(
        self,
        node: DAGNode,
        context: RuntimeContext,
    ) -> Any:  # Returns: LangGraph node function (complex internal type)
        """
        Create node function from DAG node.

        Uses NodeFactoryRegistry to get the appropriate factory function.
        This follows the factory pattern.

        Note:
            Return type is `Any` because LangGraph's node types are complex
            internal types that are not easily expressible in type hints.
            The actual return type is an async function that takes
            DialogueState | dict[str, Any] and returns dict[str, Any] (state updates).
        """
        # Ensure nodes package is imported to register factories
        # This is done lazily to avoid circular imports
        from soni.dm import nodes  # noqa: F401
        from soni.dm.node_factory_registry import NodeFactoryRegistry

        # Branch nodes don't have factories - they're handled by conditional edges
        if node.type == NodeType.BRANCH:
            # Branch nodes are pass-through - routing is handled by conditional edges
            async def branch_node(state: DialogueState | dict[str, Any]) -> dict[str, Any]:
                """Pass-through node for branches - routing handled by conditional edges."""
                # TypedDict is structurally a dict, safe to return directly
                # LangGraph always passes dict, not TypedDict at runtime
                return dict(state)

            return branch_node

        # Get factory from registry and create node
        factory = NodeFactoryRegistry.get(node.type)
        return factory(node, context)

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

        return SoniDU()
