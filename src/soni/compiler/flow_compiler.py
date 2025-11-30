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

        # Generate DAG using StepCompiler (for backward compatibility)
        dag = self.compiler._generate_dag(flow_name, parsed_steps)

        return dag

    def compile_flow_to_graph(
        self,
        flow_name: str,
    ) -> Any:  # StateGraph[DialogueState]
        """
        Compile flow directly to LangGraph StateGraph.

        Args:
            flow_name: Name of the flow to compile

        Returns:
            Compiled StateGraph ready for execution

        Raises:
            KeyError: If flow_name is not found in config
        """
        if flow_name not in self.config.flows:
            raise KeyError(f"Flow '{flow_name}' not found in configuration")

        flow_config = self.config.flows[flow_name]
        logger.info(f"Compiling flow '{flow_name}' to graph with {len(flow_config.steps)} steps")

        # Parse steps
        parsed_steps = self.parser.parse(flow_config.steps)

        # Compile to graph
        graph = self.compiler.compile(flow_name, parsed_steps)

        return graph
