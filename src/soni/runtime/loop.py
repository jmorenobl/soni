"""Runtime loop for dialogue processing.

Implements the main entry point for processing dialogue messages.
Uses dependency injection via RuntimeContext for testability.
"""

import logging
from typing import Any, cast

from langchain_core.messages import HumanMessage
from langchain_core.runnables import RunnableConfig
from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.graph.state import CompiledStateGraph

from soni.actions.handler import ActionHandler
from soni.actions.registry import ActionRegistry
from soni.core.config import SoniConfig
from soni.core.errors import StateError
from soni.core.state import create_empty_dialogue_state
from soni.core.types import DUProtocol, RuntimeContext
from soni.dm.builder import build_orchestrator
from soni.du.modules import SoniDU
from soni.flow.manager import FlowManager

logger = logging.getLogger(__name__)


class RuntimeLoop:
    """Main runtime for processing dialogue messages.

    Provides async-first interface for dialogue processing with:
    - Lazy initialization of components
    - Dependency injection via RuntimeContext
    - Checkpointer integration for state persistence
    """

    def __init__(
        self,
        config: SoniConfig,
        checkpointer: BaseCheckpointSaver | None = None,
        registry: ActionRegistry | None = None,
        du: DUProtocol | None = None,
    ):
        """Initialize RuntimeLoop.

        Args:
            config: Soni configuration with flow definitions.
            checkpointer: Optional checkpointer for state persistence.
            registry: Optional action registry. Created if not provided.
            du: Optional Dialogue Understanding module (dependency injection).
        """
        self.config = config
        self.checkpointer = checkpointer
        self._initial_registry = registry
        self._custom_du = du

        # Lazy initialization - set during initialize()
        self._flow_manager: FlowManager | None = None
        self._du: DUProtocol | None = None
        self._action_registry: ActionRegistry | None = None
        self._action_handler: ActionHandler | None = None
        self._graph: CompiledStateGraph | None = None

    @property
    def flow_manager(self) -> FlowManager:
        """Get FlowManager, raising if not initialized."""
        if not self._flow_manager:
            raise StateError("RuntimeLoop not initialized. Call initialize() first.")
        return self._flow_manager

    @flow_manager.setter
    def flow_manager(self, value: FlowManager | None) -> None:
        self._flow_manager = value

    @property
    def du(self) -> DUProtocol:
        """Get DU module, raising if not initialized."""
        if not self._du:
            raise StateError("RuntimeLoop not initialized. Call initialize() first.")
        return self._du

    @du.setter
    def du(self, value: DUProtocol | None) -> None:
        self._du = value

    @property
    def action_handler(self) -> ActionHandler:
        """Get ActionHandler, raising if not initialized."""
        if not self._action_handler:
            raise StateError("RuntimeLoop not initialized. Call initialize() first.")
        return self._action_handler

    @property
    def graph(self) -> CompiledStateGraph | None:
        """Get compiled graph."""
        return self._graph

    async def initialize(self) -> None:
        """Initialize all components.

        Safe to call multiple times - will skip if already initialized.
        """
        if self._graph:
            return

        self._flow_manager = FlowManager()

        # Use injected DU or create default factory
        if self._custom_du:
            self._du = self._custom_du
        else:
            # Use factory to auto-load best optimized model
            self._du = SoniDU.create_with_best_model(use_cot=True)

        self._action_registry = self._initial_registry or ActionRegistry()
        self._action_handler = ActionHandler(self._action_registry)

        # Compile graph with checkpointer
        orchestrator = build_orchestrator(self.config, self.checkpointer)
        self._graph = cast(CompiledStateGraph, orchestrator)

    async def process_message(self, message: str, user_id: str = "default") -> str:
        """Process a user message and return response.

        Args:
            message: User's input message.
            user_id: Unique identifier for conversation thread.

        Returns:
            System's response string.

        Raises:
            StateError: If initialization failed.
        """
        if not self._graph:
            await self.initialize()

        graph = self._graph
        if not graph:
            raise StateError("Graph initialization failed")

        # Create runtime context for dependency injection
        context = RuntimeContext(
            config=self.config,
            flow_manager=self.flow_manager,
            action_handler=self.action_handler,
            du=self.du,
        )

        run_config: dict[str, Any] = {"configurable": {"thread_id": user_id}}

        # Determine input state
        current_state = await self.get_state(user_id)

        if not current_state:
            # Initialize fresh state
            init_state = create_empty_dialogue_state()
            init_state["user_message"] = message
            init_state["messages"] = [HumanMessage(content=message)]
            init_state["turn_count"] = 1
            input_payload: Any = init_state
        else:
            # Just update message
            input_payload = {"user_message": message}
            # Append user message to history provided by reducer
            input_payload["messages"] = [HumanMessage(content=message)]
            turn_count = current_state.get("turn_count", 0)
            input_payload["turn_count"] = int(turn_count) + 1

        # Inject context via configurable
        run_config["configurable"]["runtime_context"] = context

        # Execute graph
        final_config = cast(RunnableConfig, run_config)
        result = await graph.ainvoke(input_payload, config=final_config)

        # Extract response
        # We need to return all new AI messages generated in this turn
        # Identify new messages by comparing with pre-execution count?
        # A simpler way is to filter messages by the current run? No, persistence keeps all.

        # Strategy: We assume standard AIMessages are appended.
        # But for now, let's use a simple heuristic:
        # Collect all messages that are NOT HumanMessage at the end of the list?
        # No, that might capture old history.

        # Better: Capture start length.
        start_len = len(input_payload.get("messages", []))
        # Wait, input_payload messages might be merged?
        # Actually input_payload["messages"] only had [HumanMessage].
        # But 'current_state' from get_state had full history.

        # If we loaded history, start_len is len(current_state["messages"]).
        history = current_state.get("messages", []) if current_state else []
        start_len = len(history) + 1  # +1 for the human message we just added

        final_messages = result.get("messages", [])
        new_messages = final_messages[start_len:]

        if new_messages:
            return "\n\n".join([str(m.content) for m in new_messages if hasattr(m, "content")])

        last_response = result.get("last_response")
        if last_response:
            return str(last_response)

        if final_messages and hasattr(final_messages[-1], "content"):
            return str(final_messages[-1].content)

        return "I don't understand."

    async def get_state(self, user_id: str) -> dict[str, Any] | None:
        """Get current state snapshot for a user.

        Args:
            user_id: Unique identifier for conversation thread.

        Returns:
            State dictionary or None if no state exists.
        """
        if not self._graph:
            return None

        config: dict[str, Any] = {"configurable": {"thread_id": user_id}}

        try:
            state_config = cast(RunnableConfig, config)
            snapshot = await self._graph.aget_state(state_config)
            if snapshot and snapshot.values:
                return dict(snapshot.values)
        except StateError:
            logger.warning(f"Failed to get state for user {user_id}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error getting state: {e}", exc_info=True)
            return None

        return None
