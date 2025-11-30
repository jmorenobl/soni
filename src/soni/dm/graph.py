"""LangGraph graph builder and nodes for Soni Framework"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from langgraph.graph import END, START, StateGraph

if TYPE_CHECKING:
    from contextlib import AbstractAsyncContextManager

    from langgraph.checkpoint.base import BaseCheckpointSaver
    from langgraph.graph.graph import CompiledStateGraph

from soni.actions.base import ActionHandler
from soni.compiler.dag import FlowDAG, NodeType
from soni.compiler.flow_compiler import FlowCompiler
from soni.core.config import SoniConfig
from soni.core.interfaces import (
    IActionHandler,
    INLUProvider,
    INormalizer,
    IScopeManager,
)
from soni.core.scope import ScopeManager
from soni.core.state import DialogueState, RuntimeContext
from soni.dm.nodes import (
    create_action_node_factory,
    create_collect_node_factory,
    create_understand_node,
)
from soni.dm.persistence import CheckpointerFactory
from soni.dm.validators import FlowValidator
from soni.du.modules import SoniDU
from soni.du.normalizer import SlotNormalizer

logger = logging.getLogger(__name__)

# Node functions moved to dm/nodes.py
# All node creation is now done through nodes.py factories


class SoniGraphBuilder:
    """
    Builds LangGraph StateGraph from Soni configuration.

    This builder creates graphs for linear flows (MVP only).
    Future versions will support branches and jumps.
    """

    def __init__(
        self,
        config: SoniConfig,
        scope_manager: IScopeManager | None = None,
        normalizer: INormalizer | None = None,
        nlu_provider: INLUProvider | None = None,
        action_handler: IActionHandler | None = None,
    ):
        """
        Initialize the graph builder.

        Args:
            config: Validated Soni configuration
            scope_manager: Optional scope manager (defaults to ScopeManager)
            normalizer: Optional normalizer (defaults to SlotNormalizer)
            nlu_provider: Optional NLU provider (defaults to SoniDU)
            action_handler: Optional action handler (defaults to ActionHandler)
        """
        self.config = config
        self._checkpointer_cm: AbstractAsyncContextManager[BaseCheckpointSaver] | None = None
        self.checkpointer: BaseCheckpointSaver | None = None

        # Initialize dependencies with dependency injection
        # Use provided implementations or create defaults
        self.scope_manager = scope_manager or ScopeManager(config=self.config)
        self.normalizer = normalizer or SlotNormalizer(config=self.config)
        self.nlu_provider = nlu_provider or SoniDU(scope_manager=self.scope_manager)
        # action_handler must be provided or created, cannot be None
        if action_handler is None:
            self.action_handler: IActionHandler = ActionHandler(config=self.config)
        else:
            self.action_handler = action_handler

        # Initialize flow validator and compiler
        self.validator = FlowValidator(config=self.config)
        self.compiler = FlowCompiler(config=self.config)

        # Understand node will be created in build_manual with RuntimeContext
        # This allows it to access config for normalization
        self._understand_node = None

    async def initialize(self) -> None:
        """
        Initialize the checkpointer asynchronously.

        This method must be called before using the builder to ensure
        the checkpointer is properly initialized with async context manager.

        Raises:
            Exception: If checkpointer initialization fails
        """
        if self.checkpointer is None:
            self.checkpointer, self._checkpointer_cm = await CheckpointerFactory.create(
                self.config.settings.persistence
            )

    async def cleanup(self) -> None:
        """
        Cleanup resources, especially the checkpointer context manager.

        Should be called when the builder is no longer needed to ensure
        proper resource cleanup (file descriptors, database connections, etc.).
        """
        if self._checkpointer_cm is not None:
            try:
                await self._checkpointer_cm.__aexit__(None, None, None)
                logger.info("Checkpointer context manager closed successfully")
            except Exception as e:
                logger.warning(f"Error closing checkpointer context manager: {e}")
            finally:
                self._checkpointer_cm = None
                self.checkpointer = None

    def __del__(self) -> None:
        """
        Destructor to ensure cleanup is called when object is garbage collected.

        Note: Relying on __del__ is not ideal, but provides a safety net.
        Since cleanup() is now async, __del__ cannot call it directly.
        Explicit cleanup() calls are preferred.
        """
        # Note: Cannot call async cleanup() from __del__
        # Resources will be cleaned up when context manager exits
        pass

    async def build_manual(self, flow_name: str) -> CompiledStateGraph:
        """
        Build a linear graph manually from flow configuration.

        Args:
            flow_name: Name of the flow to build

        Returns:
            Compiled StateGraph ready for execution

        Raises:
            ValueError: If flow_name is not found in config
        """
        # Initialize checkpointer if not already initialized
        if self.checkpointer is None:
            await self.initialize()

        # Validate flow using validator
        self.validator.validate_flow(flow_name)

        # Compile flow to DAG
        dag = self.compiler.compile_flow(flow_name)
        logger.info(
            f"Compiled flow '{flow_name}' to DAG with {len(dag.nodes)} nodes "
            f"and {len(dag.edges)} edges"
        )

        # Create runtime context with all dependencies
        context = RuntimeContext(
            config=self.config,
            scope_manager=self.scope_manager,
            normalizer=self.normalizer,
            action_handler=self.action_handler,
            du=self.nlu_provider,
        )

        # Build StateGraph from DAG
        graph = self._build_from_dag(dag, context)

        logger.info(f"Graph built successfully with {len(dag.nodes)} nodes")

        # Compile graph with checkpointer
        if self.checkpointer:
            return graph.compile(checkpointer=self.checkpointer)
        else:
            return graph.compile()

    def _build_from_dag(self, dag: FlowDAG, context: RuntimeContext) -> StateGraph:
        """
        Build LangGraph StateGraph from DAG.

        Args:
            dag: FlowDAG intermediate representation
            context: Runtime context with dependencies

        Returns:
            StateGraph ready for compilation
        """
        graph = StateGraph(DialogueState)

        # Add nodes from DAG
        for node in dag.nodes:
            node_fn = self._create_node_function_from_dag(node, context)
            graph.add_node(node.id, node_fn)

        # Add edges from DAG
        for edge in dag.edges:
            if edge.source == "__start__":
                graph.add_edge(START, edge.target)
            elif edge.target == "__end__":
                graph.add_edge(edge.source, END)
            else:
                # Regular edge
                graph.add_edge(edge.source, edge.target)

        return graph

    def _create_node_function_from_dag(
        self, node: Any, context: RuntimeContext
    ) -> Any:  # Node function type is complex, keep Any for now
        """
        Create node function from DAG node.

        Args:
            node: DAG node
            context: Runtime context

        Returns:
            Node function for LangGraph
        """
        if node.type == NodeType.UNDERSTAND:
            return create_understand_node(
                scope_manager=context.scope_manager,
                normalizer=context.normalizer,
                nlu_provider=context.du,
                context=context,
            )
        elif node.type == NodeType.COLLECT:
            slot_name = node.config["slot_name"]
            return create_collect_node_factory(slot_name, context)
        elif node.type == NodeType.ACTION:
            action_name = node.config["action_name"]
            return create_action_node_factory(action_name, context)
        else:
            raise ValueError(f"Unsupported node type: {node.type}")
