"""Runtime loop for dialogue processing.

Orchestrates dialogue processing using specialized components:
- RuntimeInitializer: Component creation and wiring
- StateHydrator: State preparation for graph execution
- ResponseExtractor: Response extraction from graph output

This follows SRP by delegating specific responsibilities to dedicated classes.
"""

import logging
from typing import Any, cast

from langchain_core.runnables import RunnableConfig
from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.graph.state import CompiledStateGraph

from soni.actions.handler import ActionHandler
from soni.actions.registry import ActionRegistry
from soni.core.config import SoniConfig
from soni.core.errors import StateError
from soni.core.types import DUProtocol, RuntimeContext, SlotExtractorProtocol
from soni.flow.manager import FlowManager
from soni.runtime.extractor import ResponseExtractor
from soni.runtime.hydrator import StateHydrator
from soni.runtime.initializer import RuntimeComponents, RuntimeInitializer

logger = logging.getLogger(__name__)


class RuntimeLoop:
    """Main runtime for processing dialogue messages.

    Provides async-first interface for dialogue processing.
    Delegates component creation, state preparation, and response
    extraction to specialized classes following SRP.
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
        self._initializer = RuntimeInitializer(config, checkpointer, registry, du)
        self._hydrator = StateHydrator()
        self._extractor = ResponseExtractor()

        # Components set during initialization
        self._components: RuntimeComponents | None = None

    # Property accessors for backwards compatibility
    @property
    def flow_manager(self) -> FlowManager:
        """Get FlowManager, raising if not initialized."""
        if not self._components:
            raise StateError("RuntimeLoop not initialized. Call initialize() first.")
        return self._components.flow_manager

    @flow_manager.setter
    def flow_manager(self, value: FlowManager | None) -> None:
        if self._components:
            self._components.flow_manager = value  # type: ignore

    @property
    def du(self) -> DUProtocol:
        """Get DU module, raising if not initialized."""
        if not self._components:
            raise StateError("RuntimeLoop not initialized. Call initialize() first.")
        return self._components.du

    @du.setter
    def du(self, value: DUProtocol | None) -> None:
        if self._components:
            self._components.du = value  # type: ignore

    @property
    def action_handler(self) -> ActionHandler:
        """Get ActionHandler, raising if not initialized."""
        if not self._components:
            raise StateError("RuntimeLoop not initialized. Call initialize() first.")
        return self._components.action_handler

    @property
    def slot_extractor(self) -> SlotExtractorProtocol | None:
        """Get SlotExtractor if initialized."""
        return self._components.slot_extractor if self._components else None

    @property
    def graph(self) -> CompiledStateGraph | None:
        """Get compiled graph."""
        return self._components.graph if self._components else None

    async def initialize(self) -> None:
        """Initialize all components.

        Safe to call multiple times - will skip if already initialized.
        """
        if self._components:
            return

        self._components = await self._initializer.initialize()

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
        if not self._components:
            await self.initialize()

        if not self._components or not self._components.graph:
            raise StateError("Graph initialization failed")

        graph = self._components.graph

        # Create runtime context for dependency injection
        context = RuntimeContext(
            config=self.config,
            flow_manager=self.flow_manager,
            action_handler=self.action_handler,
            du=self.du,
            slot_extractor=self.slot_extractor,
        )

        # Get current state and prepare input
        current_state = await self.get_state(user_id)
        input_payload = self._hydrator.prepare_input(message, current_state)
        history = current_state.get("messages", []) if current_state else []

        # Build config with thread and context
        run_config: dict[str, Any] = {
            "configurable": {
                "thread_id": user_id,
                "runtime_context": context,
            }
        }

        # Execute graph
        final_config = cast(RunnableConfig, run_config)
        result = await graph.ainvoke(input_payload, config=final_config)

        # Extract and return response
        return self._extractor.extract(result, input_payload, history)

    async def get_state(self, user_id: str) -> dict[str, Any] | None:
        """Get current state snapshot for a user.

        Args:
            user_id: Unique identifier for conversation thread.

        Returns:
            State dictionary or None if no state exists.
        """
        if not self._components or not self._components.graph:
            return None

        config: dict[str, Any] = {"configurable": {"thread_id": user_id}}

        try:
            state_config = cast(RunnableConfig, config)
            snapshot = await self._components.graph.aget_state(state_config)
            if snapshot and snapshot.values:
                return dict(snapshot.values)
        except StateError:
            logger.warning(f"Failed to get state for user {user_id}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error getting state: {e}", exc_info=True)
            return None

        return None

    async def reset_state(self, user_id: str) -> bool:
        """Reset conversation state for a user.

        Args:
            user_id: The user/thread ID to reset

        Returns:
            True if state was reset, False if no state existed

        Raises:
            StateError: If reset fails due to persistence error
        """
        if not self._components:
            logger.warning("reset_state called before initialization")
            return False

        checkpointer = self._components.checkpointer

        if checkpointer is None:
            # No persistence - state is already ephemeral
            logger.info(f"No checkpointer configured, state for {user_id} is ephemeral")
            # If we were tracking in-memory state in runtime self._state or similar, we would clear it here.
            # Currently LangGraph holds state. If no checkpointer, compiled graph holds in-memory state?
            # Standard CompiledGraph without checkpointer keeps state in memory per invocation usually,
            # but if we are using "thread_id" in config without a checkpointer, LangGraph might complain or use MemorySaver default?
            return True

        try:
            # LangGraph checkpointer API for clearing state
            config = {"configurable": {"thread_id": user_id}}

            # Check if state exists first
            current = await self.get_state(user_id)
            if current is None:
                logger.debug(f"No state to reset for user {user_id}")
                return False

            # Delete the checkpoint for this thread
            if hasattr(checkpointer, "adelete"):
                await checkpointer.adelete(config)
            elif hasattr(checkpointer, "delete"):
                checkpointer.delete(config)
            else:
                # Fallback: Write empty state
                from soni.core.state import create_empty_dialogue_state

                empty_state = create_empty_dialogue_state()
                # We need a way to force-write state.
                # Usually graph.update_state?
                if self._components.graph:
                    # Config for update requires thread_id
                    await self._components.graph.aupdate_state(
                        cast(RunnableConfig, config), empty_state
                    )

            logger.info(f"Reset state for user {user_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to reset state for {user_id}: {e}")
            raise StateError(f"Reset failed: {e}") from e
