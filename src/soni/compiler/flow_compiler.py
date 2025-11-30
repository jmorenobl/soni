"""Flow compiler that translates YAML flow configuration to DAG"""

import logging
from typing import Any

from soni.compiler.builder import StepCompiler
from soni.compiler.dag import FlowDAG
from soni.compiler.parser import StepParser
from soni.core.config import SoniConfig
from soni.core.interfaces import IActionHandler, INLUProvider, INormalizer, IScopeManager

logger = logging.getLogger(__name__)


class FlowCompiler:
    """Compiles YAML flow configuration to intermediate DAG."""

    def __init__(
        self,
        config: SoniConfig,
        nlu_provider: INLUProvider | None = None,
        normalizer: INormalizer | None = None,
        scope_manager: IScopeManager | None = None,
        action_handler: IActionHandler | None = None,
    ):
        """
        Initialize FlowCompiler with configuration.

        Args:
            config: Soni configuration containing flows
            nlu_provider: Optional NLU provider
            normalizer: Optional normalizer
            scope_manager: Optional scope manager
            action_handler: Optional action handler
        """
        self.config = config
        self.parser = StepParser()
        self.compiler = StepCompiler(
            config=config,
            nlu_provider=nlu_provider,
            normalizer=normalizer,
            scope_manager=scope_manager,
            action_handler=action_handler,
        )

    def compile_flow(self, flow_name: str) -> FlowDAG:
        """
        Compile a flow to intermediate DAG representation.

        This method compiles a YAML flow configuration to a FlowDAG,
        which is an intermediate representation that can be used for:
        - Graph validation and analysis
        - Transformation before building StateGraph
        - Debugging and visualization

        Use this method when you need:
        - The intermediate DAG representation
        - To inspect or modify the DAG before building StateGraph
        - To validate the flow structure independently

        Args:
            flow_name: Name of the flow to compile

        Returns:
            FlowDAG intermediate representation

        Raises:
            KeyError: If flow_name is not found in config

        Example:
            >>> compiler = FlowCompiler(config)
            >>> dag = compiler.compile_flow("booking")
            >>> print(f"Flow has {len(dag.nodes)} nodes")
        """
        if flow_name not in self.config.flows:
            raise KeyError(f"Flow '{flow_name}' not found in configuration")

        flow_config = self.config.flows[flow_name]
        steps = flow_config.steps_or_process
        logger.info(f"Compiling flow '{flow_name}' with {len(steps)} steps")

        # Parse steps first
        parsed_steps = self.parser.parse(steps)

        # Generate DAG using StepCompiler (for backward compatibility)
        dag = self.compiler._generate_dag(flow_name, parsed_steps)

        return dag

    def compile_flow_to_graph(
        self,
        flow_name: str,
    ) -> Any:  # Returns: StateGraph[DialogueState]
        """
        Compile flow directly to LangGraph StateGraph.

        This method compiles a YAML flow configuration directly to a
        LangGraph StateGraph, skipping the intermediate DAG representation.

        Use this method when you need:
        - A ready-to-use StateGraph for execution
        - Direct compilation without intermediate steps
        - Simpler code path (one method call)

        Note:
            This method internally uses `compile_flow()` and then builds
            the StateGraph from the DAG. If you need the DAG for validation
            or transformation, use `compile_flow()` instead.

            Return type is `Any` because LangGraph's `StateGraph` type is
            a complex internal type that is not easily expressible in Python
            type hints. The actual return type is `StateGraph[DialogueState]`.

        Args:
            flow_name: Name of the flow to compile

        Returns:
            Compiled StateGraph ready for execution.
            Type: StateGraph[DialogueState] (annotated as Any due to LangGraph internals)

        Raises:
            KeyError: If flow_name is not found in config

        Example:
            >>> compiler = FlowCompiler(config)
            >>> graph = compiler.compile_flow_to_graph("booking")
            >>> compiled = graph.compile(checkpointer=checkpointer)
        """
        if flow_name not in self.config.flows:
            raise KeyError(f"Flow '{flow_name}' not found in configuration")

        flow_config = self.config.flows[flow_name]
        steps = flow_config.steps_or_process
        logger.info(f"Compiling flow '{flow_name}' to graph with {len(steps)} steps")

        # Parse steps
        parsed_steps = self.parser.parse(steps)

        # Compile to graph
        graph = self.compiler.compile(flow_name, parsed_steps)

        return graph
