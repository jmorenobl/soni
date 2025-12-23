"""RuntimeLoop for M7 (ADR-002 compliant interrupt architecture)."""

import sys
from typing import TYPE_CHECKING, Any

from langchain_core.runnables import RunnableConfig
from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.graph.state import CompiledStateGraph
from langgraph.types import Command

from soni.config.models import SoniConfig
from soni.core.state import create_empty_state
from soni.core.types import DialogueState
from soni.dm.builder import build_orchestrator, compile_all_subgraphs
from soni.du.modules import SoniDU
from soni.flow.manager import FlowManager
from soni.runtime.context import RuntimeContext

if TYPE_CHECKING:
    from soni.actions.registry import ActionRegistry
    from soni.core.message_sink import MessageSink


class RuntimeLoop:
    """Runtime loop for M7 with ADR-002 interrupt architecture.

    Uses LangGraph's native interrupt/resume mechanism for multi-turn flows.
    """

    def __init__(
        self,
        config: SoniConfig,
        checkpointer: BaseCheckpointSaver | None = None,
        action_registry: "ActionRegistry | None" = None,
        message_sink: "MessageSink | None" = None,
    ) -> None:
        self.config = config
        self.checkpointer = checkpointer
        self._action_registry = action_registry
        self._message_sink = message_sink
        self._graph: CompiledStateGraph[DialogueState, RuntimeContext, Any, Any] | None = None
        self._context: RuntimeContext | None = None

    async def __aenter__(self) -> "RuntimeLoop":
        """Initialize graphs, NLU modules, and action registry."""
        # Compile ALL subgraphs upfront (ADR-002)
        subgraphs = compile_all_subgraphs(self.config)

        # Create flow manager and NLU modules (two-pass)
        flow_manager = FlowManager()
        du = SoniDU.create_with_best_model()  # Pass 1: Intent detection

        from soni.du.slot_extractor import SlotExtractor

        slot_extractor = SlotExtractor.create_with_best_model()  # Pass 2: Slot extraction

        # Use provided registry or create empty one
        from soni.actions.registry import ActionRegistry

        action_registry = self._action_registry or ActionRegistry()

        # M8: Initialize rephraser if enabled
        rephraser = None
        if self.config.settings.rephrase_responses:
            from soni.du.rephraser import ResponseRephraser

            rephraser = ResponseRephraser.create_with_best_model()
            rephraser.tone = self.config.settings.rephrase_tone

        # Create message sink (M7: ADR-002)
        from soni.core.message_sink import BufferedMessageSink

        message_sink = self._message_sink or BufferedMessageSink()

        # ADR-002: Pass subgraphs to context
        self._context = RuntimeContext(
            config=self.config,
            flow_manager=flow_manager,
            subgraph_registry=subgraphs,  # Updated name
            message_sink=message_sink,  # Added sink
            nlu_provider=du,  # Updated name (du -> nlu_provider)
            slot_extractor=slot_extractor,
            action_registry=action_registry,
            rephraser=rephraser,
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
        """Process a message and return response.

        With ADR-002 architecture:
        - First turn: Fresh invoke, may interrupt waiting for input
        - Subsequent turns: Resume from interrupt with user's response
        """
        if self._graph is None or self._context is None:
            raise RuntimeError("RuntimeLoop not initialized. Use 'async with' context.")

        # Thread config for persistence
        thread_id = f"thread_{user_id}"
        config: RunnableConfig = {"configurable": {"thread_id": thread_id}}

        try:
            # Check for existing state (persistence)
            snapshot = None
            if self.checkpointer:
                snapshot = await self._graph.aget_state(config)

            if snapshot and snapshot.tasks:
                # Resuming from interrupt (ADR-002 simplified)
                # Native LangGraph resume: pass message via Command(resume=...)
                # The message will be picked up by human_input_gate node.
                result = await self._graph.ainvoke(
                    Command(resume=message),
                    config=config,
                    context=self._context,
                )
            else:
                # Fresh execution (ADR-002)
                # First invoke goes directly to human_input_gate with user_message
                state = create_empty_state()
                state["user_message"] = message
                result = await self._graph.ainvoke(
                    state,
                    config=config,
                    context=self._context,
                )

            # Handle response (return prompt to user)
            # In the new architecture, prompts are sent to MessageSink
            # and response field is used for final confirmations or fallback.

            if "_pending_responses" in result and result["_pending_responses"]:
                return "\n".join(result["_pending_responses"])

            return str(result.get("response") or "")

        except Exception:
            import traceback

            traceback.print_exc(file=sys.stderr)

            # Try to get response from snapshot if available
            if self.checkpointer:
                try:
                    snapshot = await self._graph.aget_state(config)
                    if snapshot and snapshot.values:
                        response = snapshot.values.get("response")
                        if response:
                            return str(response)
                except Exception:
                    pass

            raise
