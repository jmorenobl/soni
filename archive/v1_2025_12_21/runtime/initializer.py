"""Runtime Initializer - Component creation for RuntimeLoop.

Extracted from RuntimeLoop to follow Single Responsibility Principle.
Responsible solely for creating and wiring runtime components.
"""

import logging
from typing import cast

from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.graph.state import CompiledStateGraph
from soni.actions.handler import ActionHandler
from soni.actions.registry import ActionRegistry
from soni.core.types import DUProtocol, SlotExtractorProtocol
from soni.dm.builder import build_orchestrator
from soni.du.modules import SoniDU
from soni.du.slot_extractor import SlotExtractor
from soni.flow.manager import FlowManager

from soni.config import SoniConfig

logger = logging.getLogger(__name__)


class RuntimeComponents:
    """Container for initialized runtime components."""

    def __init__(
        self,
        flow_manager: FlowManager,
        du: DUProtocol,
        slot_extractor: SlotExtractorProtocol,
        action_registry: ActionRegistry,
        action_handler: ActionHandler,
        graph: CompiledStateGraph,
        subgraphs: dict[str, CompiledStateGraph],
        checkpointer: BaseCheckpointSaver | None = None,
    ):
        self.flow_manager = flow_manager
        self.du = du
        self.slot_extractor = slot_extractor
        self.action_registry = action_registry
        self.action_handler = action_handler
        self.graph = graph
        self.subgraphs = subgraphs
        self.checkpointer = checkpointer


class RuntimeInitializer:
    """Initializes runtime components for dialogue processing.

    SRP: Sole responsibility is component creation and wiring.
    """

    def __init__(
        self,
        config: SoniConfig,
        checkpointer: BaseCheckpointSaver | None = None,
        registry: ActionRegistry | None = None,
        du: DUProtocol | None = None,
        slot_extractor: SlotExtractorProtocol | None = None,
    ):
        """Initialize the initializer.

        Args:
            config: Soni configuration with flow definitions.
            checkpointer: Optional checkpointer for state persistence.
            registry: Optional action registry. Created if not provided.
            du: Optional pre-configured DU module (dependency injection).
            slot_extractor: Optional pre-configured slot extractor (dependency injection).
        """
        self.config = config
        self.checkpointer = checkpointer
        self._initial_registry = registry
        self._custom_du = du
        self._custom_slot_extractor = slot_extractor

    async def initialize(self) -> RuntimeComponents:
        """Create and wire all runtime components.

        Returns:
            RuntimeComponents container with all initialized components.
        """
        flow_manager = FlowManager()

        # Use injected DU or create default factory
        if self._custom_du:
            du = self._custom_du
        else:
            # Use factory to auto-load best optimized model
            du = SoniDU.create_with_best_model(use_cot=True)

        # Initialize slot extractor for Pass 2 of two-pass NLU
        # Use injected or create default
        if self._custom_slot_extractor is not None:
            slot_extractor = self._custom_slot_extractor
        else:
            slot_extractor = SlotExtractor.create_with_best_model(use_cot=False)

        action_registry = self._initial_registry or ActionRegistry()
        action_handler = ActionHandler(action_registry)

        # Compile graph with checkpointer
        # build_orchestrator now returns (graph, subgraphs)
        graph_runnable, subgraphs = build_orchestrator(self.config, self.checkpointer)
        graph = cast(CompiledStateGraph, graph_runnable)

        logger.info("Runtime components initialized successfully")

        return RuntimeComponents(
            flow_manager=flow_manager,
            du=du,
            slot_extractor=slot_extractor,
            action_registry=action_registry,
            action_handler=action_handler,
            graph=graph,
            subgraphs=subgraphs,
            checkpointer=self.checkpointer,
        )
