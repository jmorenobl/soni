"""Runtime loop for dialogue processing.

Orchestrates dialogue processing using specialized components:
- RuntimeInitializer: Component creation and wiring
- StateHydrator: State preparation for graph execution
- ResponseExtractor: Response extraction from graph output

This follows SRP by delegating specific responsibilities to dedicated classes.
"""

import logging
from collections.abc import AsyncIterator
from types import TracebackType
from typing import Any, cast

from langchain_core.runnables import RunnableConfig
from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.graph.state import CompiledStateGraph
from langgraph.types import StreamMode

from soni.actions.handler import ActionHandler
from soni.actions.registry import ActionRegistry
from soni.config import SoniConfig
from soni.core.errors import StateError
from soni.core.types import DUProtocol, RuntimeContext, SlotExtractorProtocol
from soni.flow.manager import FlowManager
from soni.runtime.extractor import ResponseExtractor
from soni.runtime.hydrator import StateHydrator
from soni.runtime.initializer import RuntimeComponents, RuntimeInitializer

logger = logging.getLogger(__name__)


class RuntimeLoop:
    """Main runtime for processing dialogue messages.

    Supports async context manager protocol for resource management:

        async with RuntimeLoop(config, checkpointer) as runtime:
            response = await runtime.process_message("hi", "user1")
        # Resources automatically cleaned up

    Can also be used without context manager, but cleanup() must be
    called manually to release resources.
    """

    def __init__(
        self,
        config: SoniConfig,
        checkpointer: BaseCheckpointSaver[Any] | None = None,
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
        self._cleanup_done = False  # Track cleanup state

    async def __aenter__(self) -> "RuntimeLoop":
        """Async context manager entry - initialize runtime.

        Returns:
            Self for use in `async with` statements.

        Example:
            async with RuntimeLoop(config) as runtime:
                response = await runtime.process_message("hi", "user1")
        """
        await self.initialize()
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> bool:
        """Async context manager exit - cleanup resources.

        Always performs cleanup, regardless of whether an exception occurred.

        Args:
            exc_type: Exception type if an exception was raised.
            exc_val: Exception instance if an exception was raised.
            exc_tb: Traceback if an exception was raised.

        Returns:
            False to propagate exceptions (never suppresses).
        """
        await self.cleanup()
        return False  # Don't suppress exceptions

    # Property accessors for backwards compatibility
    @property
    def flow_manager(self) -> FlowManager:
        """Get FlowManager, raising if not initialized."""
        if not self._components:
            raise StateError("RuntimeLoop not initialized. Call initialize() first.")
        return self._components.flow_manager

    @property
    def du(self) -> DUProtocol:
        """Get DU module, raising if not initialized."""
        if not self._components:
            raise StateError("RuntimeLoop not initialized. Call initialize() first.")
        return self._components.du

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
    def graph(self) -> CompiledStateGraph[Any, Any] | None:
        """Get compiled graph."""
        return self._components.graph if self._components else None

    def _has_pending_interrupt(self, state_snapshot) -> bool:
        """Check if there's a pending interrupt in the state.

        Args:
            state_snapshot: StateSnapshot from graph.aget_state()

        Returns:
            True if there's a pending interrupt, False otherwise.
        """
        if not state_snapshot or not hasattr(state_snapshot, "next"):
            return False
        # If there are pending tasks (next nodes to execute), there's an interrupt
        # Ensure it's a real list/tuple, not a mock or other object
        next_nodes = state_snapshot.next
        if next_nodes is None:
            return False
        # Check if it's a real collection (list/tuple) and not empty
        if isinstance(next_nodes, (list, tuple)):
            return len(next_nodes) > 0
        # For anything else (including mocks), return False to be safe
        return False

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
            }
        }

        # Check for pending interrupt BEFORE executing graph (only if checkpointer exists)
        has_interrupt = False
        if hasattr(graph, "checkpointer") and graph.checkpointer:
            state_snapshot = await graph.aget_state(run_config)
            has_interrupt = self._has_pending_interrupt(state_snapshot)

        # Execute graph
        final_config = cast(RunnableConfig, run_config)

        # Use Command(resume=...) pattern when resuming from interrupt
        if has_interrupt:
            # CRITICAL: Execute NLU BEFORE resuming to enable command-based approach
            # This ensures NLU always processes user input, even during interrupt/resume
            from soni.du.service import NLUService

            nlu_service = NLUService(self.du, self.slot_extractor)
            # Use current_state or empty dict if None (shouldn't happen with interrupt, but safety check)
            from soni.core.state import create_empty_dialogue_state
            from soni.core.types import DialogueState

            state_for_nlu: DialogueState = (
                cast(DialogueState, dict(current_state))  # Copy to avoid mutating original
                if current_state
                else create_empty_dialogue_state()
            )

            # Extract expected slot from interrupt metadata
            # The collect_node passes {type: "collect", slot: slot_name} in interrupt()
            if state_snapshot.interrupts:
                interrupt_value = state_snapshot.interrupts[0].value
                if isinstance(interrupt_value, dict) and "slot" in interrupt_value:
                    state_for_nlu["waiting_for_slot"] = interrupt_value["slot"]

            commands = await nlu_service.process_message(message, state_for_nlu, context)
            serialized_commands = nlu_service.serialize_commands(commands)

            # Standard Pattern: Pass NLU commands via resume payload
            # The collect_node will process them and return a Command(update=...)
            # to ensure persistence despite interrupt discard rules.
            from langgraph.types import Command

            # Prepare resume payload with serialized commands
            resume_payload = {
                "message": message,
                "commands": serialized_commands,
                **input_payload,  # user_message, messages, turn_count
            }

            # CRITICAL: Update state.commands with new commands on resume
            # Without this, old commands from previous turns persist and cause
            # nodes like confirm_node to incorrectly detect modifications
            result = await graph.ainvoke(
                Command(
                    resume=resume_payload,
                    update={
                        "_pending_responses": [],
                        "commands": serialized_commands,  # Replace old commands
                    },
                ),
                config=final_config,
                context=context,
                durability=self.config.settings.durability,
            )
        else:
            # Normal flow: start with prepared input
            # Note: LangGraph v0.6.0+ context injection API.
            # Type checking is handled via ignore_missing_imports in pyproject.toml.
            result = await graph.ainvoke(
                input_payload,
                config=final_config,
                context=context,
                durability=self.config.settings.durability,
            )
        # Check for interrupt
        if "__interrupt__" in result:
            interrupt_info = result["__interrupt__"][0]
            interrupt_value = interrupt_info.value
            prompt = interrupt_value.get("prompt", "") if isinstance(interrupt_value, dict) else ""

            # Consume pending responses queue (from completed flows like check_balance)
            pending_responses = result.get("_pending_responses", [])

            if pending_responses and prompt:
                # Combine queued responses with new prompt
                combined = "\n\n".join(pending_responses) + "\n\n" + str(prompt)
                return combined
            elif prompt:
                return str(prompt)
            elif pending_responses:
                return "\n\n".join(pending_responses)
            return ""

        # Extract and return response
        return self._extractor.extract(result, input_payload, history)

    async def process_message_streaming(
        self,
        user_message: str,
        user_id: str = "default",
        stream_mode: StreamMode = "updates",
    ) -> AsyncIterator[dict[str, Any]]:
        """Process a message with streaming output.

        Args:
            user_message: The user's input message
            user_id: User identifier for state persistence
            stream_mode: LangGraph stream mode (updates, values, custom)
                - "updates": Emit state updates after each node (recommended)
                - "values": Emit full state after each node
                - "custom": Emit custom data via get_stream_writer()

        Yields:
            Streaming chunks in format {node_name: {state_updates}}
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
        input_payload = self._hydrator.prepare_input(user_message, current_state)

        # Build config with thread and context
        run_config: dict[str, Any] = {
            "configurable": {
                "thread_id": user_id,
            }
        }

        # Same context injection as ainvoke - see comment above.
        async for chunk in graph.astream(
            input_payload,
            config=cast(RunnableConfig, run_config),
            stream_mode=stream_mode,
            context=context,
            durability=self.config.settings.durability,
        ):
            yield chunk

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
            # Delete the checkpoint for this thread (async-first)
            if hasattr(checkpointer, "adelete_thread"):
                await checkpointer.adelete_thread(user_id)
            else:
                # Fallback: Write empty state if checkpointer doesn't support deletion
                from soni.core.state import create_empty_dialogue_state

                empty_state = create_empty_dialogue_state()
                # We need a way to force-write state.
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

    async def cleanup(self) -> None:
        """Clean up runtime resources.

        Safe to call multiple times - subsequent calls are no-ops.
        Should be called during server shutdown to release resources gracefully.
        """
        if self._cleanup_done:
            logger.debug("Cleanup already completed, skipping")
            return

        logger.info("RuntimeLoop cleanup starting...")

        if not self._components:
            logger.debug("No components to clean up")
            self._cleanup_done = True
            return

        # Close checkpointer if it has a close method
        checkpointer = self._components.checkpointer
        if checkpointer:
            if hasattr(checkpointer, "aclose"):
                try:
                    await checkpointer.aclose()
                    logger.debug("Checkpointer closed (async)")
                except Exception as e:
                    logger.warning(f"Error closing checkpointer: {e}")
            elif hasattr(checkpointer, "close"):
                try:
                    checkpointer.close()
                    logger.debug("Checkpointer closed (sync)")
                except Exception as e:
                    logger.warning(f"Error closing checkpointer: {e}")

        # Clear references to allow GC
        self._components = None
        self._cleanup_done = True

        logger.info("RuntimeLoop cleanup completed")
