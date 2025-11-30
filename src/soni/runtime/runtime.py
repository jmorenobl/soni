"""Runtime loop for Soni Framework"""

import asyncio
import logging
import time
from collections.abc import AsyncGenerator
from pathlib import Path
from typing import Any

from soni.core.errors import (
    ActionNotFoundError,
    NLUError,
    PersistenceError,
    SoniError,
    ValidationError,
)
from soni.core.interfaces import (
    IActionHandler,
    INLUProvider,
    INormalizer,
    IScopeManager,
)
from soni.core.scope import ScopeManager
from soni.core.state import DialogueState
from soni.dm.graph import SoniGraphBuilder
from soni.du.modules import SoniDU
from soni.du.normalizer import SlotNormalizer
from soni.runtime.config_manager import ConfigurationManager
from soni.runtime.conversation_manager import ConversationManager
from soni.runtime.streaming_manager import StreamingManager

logger = logging.getLogger(__name__)


class RuntimeLoop:
    """
    Main runtime loop for processing user messages.

    This class orchestrates:
    - Graph execution (LangGraph)
    - NLU processing (SoniDU)
    - State persistence (checkpointing)
    - Multi-conversation management
    """

    def __init__(
        self,
        config_path: str | Path,
        optimized_du_path: str | Path | None = None,
        scope_manager: IScopeManager | None = None,
        normalizer: INormalizer | None = None,
        nlu_provider: INLUProvider | None = None,
        action_handler: IActionHandler | None = None,
    ) -> None:
        """
        Initialize RuntimeLoop with configuration.

        Args:
            config_path: Path to YAML configuration file
            optimized_du_path: Optional path to optimized SoniDU module (JSON)
            scope_manager: Optional scope manager (defaults to ScopeManager)
            normalizer: Optional normalizer (defaults to SlotNormalizer)
            nlu_provider: Optional NLU provider (defaults to SoniDU)
            action_handler: Optional action handler (defaults to ActionHandler)
        """
        # Load configuration using ConfigurationManager
        self.config_manager = ConfigurationManager(config_path)
        self.config = self.config_manager.load()

        # Build graph (checkpointer will be initialized lazily in build_manual)
        self.builder = SoniGraphBuilder(self.config)
        # Graph will be built lazily on first use (requires async)
        self.graph: Any = None
        self._flow_name: str = list(self.config.flows.keys())[0]
        # Lock to protect graph initialization from concurrent access
        self._graph_init_lock = asyncio.Lock()

        # Managers will be initialized after graph is built
        self.conversation_manager: ConversationManager | None = None
        self.streaming_manager: StreamingManager | None = None

        # Initialize dependencies with dependency injection
        # Use provided implementations or create defaults
        self.scope_manager = scope_manager or ScopeManager(config=self.config)
        self.normalizer = normalizer or SlotNormalizer(config=self.config)

        # Initialize DU module with scope_manager
        if nlu_provider is not None:
            self.du = nlu_provider
            logger.info("Using injected NLU provider")
        elif optimized_du_path and Path(optimized_du_path).exists():
            from soni.du.optimizers import load_optimized_module

            self.du = load_optimized_module(optimized_du_path)
            logger.info(f"Loaded optimized DU from {optimized_du_path}")
        else:
            self.du = SoniDU(scope_manager=self.scope_manager)
            logger.info("Using default (non-optimized) DU module")

        # Store action_handler for future use (will be used in Task 040)
        self.action_handler = action_handler

        logger.info(f"RuntimeLoop initialized with config: {config_path}")

    async def _ensure_graph_initialized(self) -> None:
        """
        Ensure graph is initialized (lazy initialization).

        This method initializes the graph asynchronously if not already done.
        Uses a lock to prevent concurrent initialization.
        """
        if self.graph is None:
            async with self._graph_init_lock:
                # Double-check pattern: another coroutine might have initialized it
                if self.graph is None:
                    self.graph = await self.builder.build_manual(self._flow_name)
                    # Initialize managers after graph is built
                    self.conversation_manager = ConversationManager(self.graph)
                    self.streaming_manager = StreamingManager()

    async def cleanup(self) -> None:
        """
        Cleanup resources, especially the graph builder's checkpointer.

        Should be called when the RuntimeLoop is no longer needed to ensure
        proper resource cleanup.
        """
        if hasattr(self, "builder") and self.builder:
            await self.builder.cleanup()
            logger.info("RuntimeLoop cleanup completed")

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

    async def process_message(
        self,
        user_msg: str,
        user_id: str,
    ) -> str:
        """
        Process a user message and return response.

        This method:
        1. Loads or creates dialogue state for user
        2. Adds user message to state
        3. Executes graph with state
        4. Extracts response from final state
        5. Saves updated state

        Args:
            user_msg: User's input message
            user_id: Unique identifier for user/conversation

        Returns:
            Response message from the dialogue system

        Raises:
            ValidationError: If inputs are invalid
            SoniError: If processing fails
        """
        # Validate inputs
        if not user_msg or not user_msg.strip():
            raise ValidationError("User message cannot be empty")

        if not user_id or not user_id.strip():
            raise ValidationError("User ID cannot be empty")

        logger.info(f"Processing message for user {user_id}: {user_msg[:50]}...")

        try:
            # Ensure graph is initialized (lazy initialization)
            await self._ensure_graph_initialized()

            # Configure checkpointing with thread_id = user_id
            config = {
                "configurable": {
                    "thread_id": user_id,
                }
            }

            # Try to load existing state from checkpoint
            existing_state_snapshot = None
            try:
                # Use aget_state() to retrieve the current checkpoint for this thread (async)
                if self.builder.checkpointer:
                    existing_state_snapshot = await self.graph.aget_state(config)
                    if existing_state_snapshot and existing_state_snapshot.values:
                        logger.info(f"Loaded existing state for user {user_id}")
                    else:
                        logger.info(f"No existing state found for user {user_id}, creating new")
            except (OSError, ConnectionError, PersistenceError) as e:
                # Errores esperados de persistencia
                logger.warning(
                    f"Checkpoint load failed, creating new state: {e}",
                    extra={
                        "user_id": user_id,
                        "error_type": type(e).__name__,
                    },
                )
                existing_state_snapshot = None
            except Exception as e:
                # Errores inesperados - no ocultar
                logger.error(
                    f"Unexpected checkpoint error: {e}",
                    exc_info=True,
                    extra={"user_id": user_id},
                )
                raise

            # Create or update state with user message
            if existing_state_snapshot and existing_state_snapshot.values:
                # Load existing state from checkpoint
                state = DialogueState.from_dict(existing_state_snapshot.values)
                state.add_message("user", user_msg)
                logger.debug(
                    f"Updated existing state: {len(state.messages)} messages, "
                    f"{len(state.slots)} slots, turn {state.turn_count}"
                )
            else:
                # Create new state
                state = DialogueState(
                    messages=[{"role": "user", "content": user_msg}],
                    current_flow="none",
                    slots={},
                )
                logger.debug("Created new state for new conversation")

            # Get scoped actions based on current state
            # Note: state.config hack removed - nodes now use RuntimeContext
            scoped_actions = self.scope_manager.get_available_actions(state)
            logger.debug(
                f"Scoped actions for user {user_id}: {scoped_actions} "
                f"(total: {len(scoped_actions)})"
            )

            # Log scoping metrics
            total_actions = len(self.config.actions) if hasattr(self.config, "actions") else 0
            scoped_count = len(scoped_actions)
            if total_actions > 0:
                reduction = (
                    ((total_actions - scoped_count) / total_actions * 100)
                    if total_actions > 0
                    else 0
                )
                logger.info(
                    f"Action scoping for user {user_id}: "
                    f"{scoped_count}/{total_actions} actions ({reduction:.1f}% reduction)",
                    extra={
                        "user_id": user_id,
                        "total_actions": total_actions,
                        "scoped_actions": scoped_count,
                        "reduction_percent": reduction,
                        "current_flow": state.current_flow,
                    },
                )

            # Execute graph
            config = {"configurable": {"thread_id": user_id}}
            result = await self.graph.ainvoke(
                state.to_dict(),
                config=config,
            )

            # Extract response from result
            # The graph should update state with last_response
            response_raw = result.get("last_response", "I'm sorry, I didn't understand that.")
            response = str(response_raw) if response_raw else "I'm sorry, I didn't understand that."

            # State is automatically saved by checkpointing
            logger.info(f"Successfully processed message for user {user_id}")
            return response

        except ValidationError as e:
            logger.error(f"Validation error for user {user_id}: {e}")
            raise
        except (NLUError, ActionNotFoundError) as e:
            # Errores esperados del diálogo
            logger.warning(
                f"Dialogue processing failed: {e}",
                extra={
                    "user_id": user_id,
                    "error_type": type(e).__name__,
                },
            )
            raise
        except Exception as e:
            # Errores inesperados del grafo
            logger.error(
                f"Unexpected graph execution error: {e}",
                exc_info=True,
                extra={
                    "user_id": user_id,
                    "graph_state": state.get("current_flow")
                    if isinstance(state, dict)
                    else getattr(state, "current_flow", None),
                },
            )
            raise SoniError(f"Failed to process message: {e}") from e

    async def process_message_stream(
        self,
        user_msg: str,
        user_id: str,
    ) -> AsyncGenerator[str, None]:
        """
        Process a user message and stream response tokens.

        This method:
        1. Loads or creates dialogue state for user
        2. Adds user message to state
        3. Streams graph execution events
        4. Yields tokens as they become available
        5. Saves updated state

        Args:
            user_msg: User's input message
            user_id: Unique identifier for user/conversation

        Yields:
            Tokens as strings (compatible with SSE format)

        Raises:
            ValidationError: If inputs are invalid
            SoniError: If processing fails
        """
        # Validate inputs
        if not user_msg or not user_msg.strip():
            raise ValidationError("User message cannot be empty")

        if not user_id or not user_id.strip():
            raise ValidationError("User ID cannot be empty")

        logger.info(f"Processing message stream for user {user_id}: {user_msg[:50]}...")
        start_time = time.time()
        first_token_sent = False

        try:
            # Ensure graph is initialized (lazy initialization)
            await self._ensure_graph_initialized()

            # Get or create state using ConversationManager
            if self.conversation_manager is None:
                raise SoniError("ConversationManager not initialized")
            state = await self.conversation_manager.get_or_create_state(user_id)
            state.add_message("user", user_msg)

            # Get scoped actions based on current state
            scoped_actions = self.scope_manager.get_available_actions(state)
            logger.debug(
                f"Scoped actions for user {user_id}: {scoped_actions} "
                f"(total: {len(scoped_actions)})"
            )

            # Stream graph execution using StreamingManager
            if self.streaming_manager is None:
                raise SoniError("StreamingManager not initialized")
            async for event in self.streaming_manager.stream_response(
                graph=self.graph,
                state=state,
                user_id=user_id,
            ):
                # Extract response from event
                # With stream_mode="updates", event is a dict where keys are node names
                # and values are the updates made by that node
                if isinstance(event, dict):
                    # Check for response updates in any node
                    for _node_name, node_update in event.items():
                        if isinstance(node_update, dict):
                            response_raw = node_update.get("last_response")
                            if response_raw:
                                response_text = str(response_raw)

                                # Split response into tokens (words for now)
                                # In future, could use actual tokenization
                                tokens = response_text.split()

                                for token in tokens:
                                    # Measure first token latency
                                    if not first_token_sent:
                                        first_token_latency = (
                                            time.time() - start_time
                                        ) * 1000  # ms
                                        logger.info(
                                            f"First token latency for user {user_id}: "
                                            f"{first_token_latency:.2f}ms"
                                        )
                                        first_token_sent = True

                                    # Yield token (SSE format will be handled by endpoint)
                                    yield token + " "

                                # Yield final newline to signal completion of this chunk
                                yield "\n"

            # State is automatically saved by checkpointing
            logger.info(f"Successfully processed message stream for user {user_id}")

        except ValidationError as e:
            logger.error(f"Validation error for user {user_id}: {e}")
            # Yield error message as token
            yield f"Error: {str(e)}\n"
            raise
        except Exception as e:
            logger.error(
                f"Unexpected error processing message stream for user {user_id}: {e}",
                exc_info=True,
            )
            # Yield error message as token
            yield "Error: Failed to process message\n"
            raise SoniError(f"Failed to process message: {e}") from e
