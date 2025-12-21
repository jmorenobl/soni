"""RuntimeLoop for M4 (NLU integration)."""

from typing import Any

from langchain_core.runnables import RunnableConfig
from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.graph.state import CompiledStateGraph
from langgraph.types import Command

from soni.compiler.subgraph import build_flow_subgraph
from soni.config.models import SoniConfig
from soni.core.state import create_empty_state
from soni.core.types import DialogueState
from soni.dm.builder import build_orchestrator
from soni.du.modules import SoniDU
from soni.flow.manager import FlowManager
from soni.runtime.context import RuntimeContext


class RuntimeLoop:
    """Runtime loop for M4 with checkpointer and NLU support."""

    def __init__(
        self,
        config: SoniConfig,
        checkpointer: BaseCheckpointSaver | None = None,
    ) -> None:
        self.config = config
        self.checkpointer = checkpointer
        self._graph: CompiledStateGraph[DialogueState, RuntimeContext, Any, Any] | None = None
        self._context: RuntimeContext | None = None

    async def __aenter__(self) -> "RuntimeLoop":
        """Initialize graphs and NLU modules (two-pass architecture)."""
        # Build subgraph for first flow
        flow_name = next(iter(self.config.flows.keys()))
        flow = self.config.flows[flow_name]
        subgraph = build_flow_subgraph(flow)

        # Create flow manager and NLU modules (two-pass)
        flow_manager = FlowManager()
        du = SoniDU.create_with_best_model()  # Pass 1: Intent detection

        from soni.du.slot_extractor import SlotExtractor
        slot_extractor = SlotExtractor.create_with_best_model()  # Pass 2: Slot extraction

        self._context = RuntimeContext(
            subgraph=subgraph,
            config=self.config,
            flow_manager=flow_manager,
            du=du,
            slot_extractor=slot_extractor,
        )

        # Build orchestrator with checkpointer
        self._graph = build_orchestrator(checkpointer=self.checkpointer)
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: Any,
    ) -> None:
        """Cleanup."""
        pass

    async def process_message(self, message: str, user_id: str = "default") -> str:
        """Process a message and return response."""
        if self._graph is None or self._context is None:
            raise RuntimeError("RuntimeLoop not initialized. Use 'async with' context.")

        state = create_empty_state()
        state["user_message"] = message

        # Thread config for persistence
        thread_id = f"thread_{user_id}"
        config: RunnableConfig = {"configurable": {"thread_id": thread_id}}

        try:
            # Check for pending interrupts (only if persistence enabled)
            snapshot = None
            if self.checkpointer:
                snapshot = await self._graph.aget_state(config)

            # Resume if interrupted
            if snapshot and snapshot.tasks:
                # Resume execution with the user message
                result = await self._graph.ainvoke(
                    Command(resume=message),
                    config=config,
                    context=self._context,
                )
            else:
                # Fresh execution
                # If no checkpointer, config might be ignored by state graph for thread_id, logic holds
                result = await self._graph.ainvoke(state, config=config, context=self._context)

            if "__interrupt__" in result:
                # Unwrap interrupt payload to get the prompt
                interruption = result["__interrupt__"]
                val = interruption

                # Unwrap list/tuple (e.g. [Interrupt(...)])
                while isinstance(val, (list, tuple)) and val:
                    val = val[0]

                # Unwrap Interrupt object
                if hasattr(val, "value"):
                    val = val.value

                if isinstance(val, dict) and "prompt" in val:
                    return str(val["prompt"])

            return str(result.get("response", ""))

        except Exception as e:
            # Check for interrupt state if exception occurs
            if self.checkpointer:
                snapshot = await self._graph.aget_state(config)
                if snapshot.values:
                    return str(snapshot.values.get("response", ""))

            # Rethrow if no persistence
            raise e
