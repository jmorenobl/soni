"""Runtime loop for Soni Framework"""

import asyncio
import logging
import time
from collections.abc import AsyncGenerator
from pathlib import Path
from typing import TYPE_CHECKING, Any

from soni.actions.base import ActionHandler
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
from soni.core.security import sanitize_user_id, sanitize_user_message
from soni.core.state import (
    DialogueState,
    add_message,
    create_initial_state,
    get_all_slots,
    get_current_flow,
    state_from_dict,
    state_to_dict,
)
from soni.dm.persistence import CheckpointerFactory

if TYPE_CHECKING:
    from contextlib import AbstractAsyncContextManager

    from langgraph.checkpoint.base import BaseCheckpointSaver
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

        # Initialize checkpointer state
        self._checkpointer_cm: AbstractAsyncContextManager[BaseCheckpointSaver] | None = None
        self.checkpointer: BaseCheckpointSaver | None = None

        # Graph will be built lazily on first use (requires async)
        self.graph: Any = None
        self._flow_name: str = list(self.config.flows.keys())[0]
        # Lock to protect graph initialization from concurrent access
        self._graph_init_lock = asyncio.Lock()
        # Flag to track cleanup status
        self._cleaned_up = False

        # Managers will be initialized after graph is built
        self.conversation_manager: ConversationManager | None = None
        self.streaming_manager: StreamingManager | None = None

        # Initialize dependencies with dependency injection
        # Use provided implementations or create defaults
        self.scope_manager = scope_manager or ScopeManager(config=self.config)
        self.normalizer = normalizer or SlotNormalizer(config=self.config)

        # Initialize DU module
        if nlu_provider is not None:
            self.du = nlu_provider
            logger.info("Using injected NLU provider")
        elif optimized_du_path and Path(optimized_du_path).exists():
            from soni.du.optimizers import load_optimized_module

            self.du = load_optimized_module(optimized_du_path)
            logger.info(f"Loaded optimized DU from {optimized_du_path}")
        else:
            # Get use_reasoning from YAML configuration (defaults to False if not set)
            # Map to use_cot for SoniDU (maintains DSPy terminology in code)
            use_reasoning = getattr(self.config.settings.models.nlu, "use_reasoning", False)
            self.du = SoniDU(use_cot=use_reasoning)
            logger.info(
                f"Using default (non-optimized) DU module with use_reasoning={use_reasoning}"
            )

        # Initialize action handler
        self.action_handler = action_handler or ActionHandler(config=self.config)

        # Auto-discover and import actions from config directory
        # Also try importing __init__.py from config directory if it exists
        # (allows custom module names like handlers.py to be imported via __init__.py)
        self._auto_import_actions(config_path)
        self._try_import_config_package(config_path)

        logger.info(f"RuntimeLoop initialized with config: {config_path}")

    def _auto_import_actions(self, config_path: str | Path) -> None:
        """Auto-discover and import actions module from config directory.

        Follows convention over configuration principle:
        - Looks for `actions.py` in config directory (primary convention)
        - Looks for `actions/__init__.py` in config directory (package convention)
        - If neither exists, actions must be imported manually before RuntimeLoop creation

        Actions are automatically registered via @ActionRegistry.register() decorator
        when the module is imported.

        For custom module names (e.g., `handlers.py`, `tools.py`), users should:
        1. Import the module in `__init__.py` of the config directory (handled by
           `_try_import_config_package`), OR
        2. Create an `actions.py` that imports from the custom module, OR
        3. Use `actions/__init__.py` and import from custom modules there, OR
        4. Import the module manually before creating RuntimeLoop

        This follows Open/Closed Principle: system is open for extension (custom imports
        via __init__.py) but closed for modification (no hardcoded module names).

        Args:
            config_path: Path to YAML configuration file
        """
        config_dir = Path(config_path).parent

        # Try actions.py (primary convention)
        actions_file = config_dir / "actions.py"
        if actions_file.exists():
            import importlib.util

            spec = importlib.util.spec_from_file_location("user_actions", actions_file)
            if spec and spec.loader:
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                logger.info(f"Auto-imported actions from {actions_file}")
                return

        # Try actions/ package (package convention)
        actions_dir = config_dir / "actions"
        if actions_dir.exists() and (actions_dir / "__init__.py").exists():
            # Add parent to sys.path temporarily
            import importlib
            import sys

            original_path = sys.path[:]
            try:
                sys.path.insert(0, str(config_dir))
                importlib.import_module("actions")
                logger.info(f"Auto-imported actions package from {actions_dir}")
            finally:
                sys.path[:] = original_path
            return

    def _try_import_config_package(self, config_path: str | Path) -> None:
        """Try importing __init__.py from config directory.

        This allows users to import custom modules (e.g., handlers.py, tools.py)
        in __init__.py, which will be executed when the package is imported.
        This follows Open/Closed Principle: users can extend behavior without
        modifying framework code.

        Args:
            config_path: Path to YAML configuration file

        Note on Module Reloading:
            If the package is already imported (cached in sys.modules), this method
            reloads it to re-execute decorators like @ActionRegistry.register().

            This is necessary when:
            - ActionRegistry is cleared between tests (test isolation)
            - Modules are imported before RuntimeLoop initialization

            In production, modules are typically imported once per process, so reload
            is rare and safe. The reload only occurs if the module is already cached,
            which is primarily a test scenario.

            This design choice balances:
            - Test isolation (registry clearing between tests)
            - Production simplicity (no special test-only code paths)
            - Safety (reload only when module already exists)
        """
        config_dir = Path(config_path).parent
        init_file = config_dir / "__init__.py"

        if init_file.exists():
            import importlib
            import sys

            # Import the package (__init__.py will be executed)
            package_name = config_dir.name
            parent_dir = config_dir.parent

            original_path = sys.path[:]
            try:
                if str(parent_dir) not in sys.path:
                    sys.path.insert(0, str(parent_dir))

                # If module already imported, reload it to re-execute decorators
                # This is important when ActionRegistry is cleared (e.g., in tests)
                # In production, modules are typically imported once, so this is rare
                if package_name in sys.modules:
                    # Reload the package and its submodules to re-execute all decorators
                    # This ensures @ActionRegistry.register() decorators are re-executed
                    package_module = sys.modules[package_name]
                    importlib.reload(package_module)

                    # Also reload submodules that may contain action registrations
                    # (e.g., handlers.py imported by __init__.py)
                    for submodule_name in list(sys.modules.keys()):
                        if submodule_name.startswith(f"{package_name}."):
                            try:
                                importlib.reload(sys.modules[submodule_name])
                            except (ImportError, AttributeError, KeyError):
                                # Submodule may not be importable - skip silently
                                pass

                    logger.debug(
                        f"Reloaded __init__.py and submodules from {config_dir} (re-registering actions)"
                    )
                else:
                    importlib.import_module(package_name)
                    logger.debug(
                        f"Imported __init__.py from {config_dir} (may register custom actions)"
                    )
            except ImportError as e:
                logger.debug(f"Could not import __init__.py from {config_dir}: {e}")
            finally:
                sys.path[:] = original_path

    async def _ensure_graph_initialized(self) -> None:
        """Ensure graph is initialized (lazy initialization).

        This method initializes the graph asynchronously if not already done.
        Uses a lock to prevent concurrent initialization.

        Uses the subgraph architecture with OrchestratorGraph:
        - understand: NLU → Commands
        - execute: Commands → State changes
        - flow_* subgraphs: One compiled StateGraph per flow
        - respond: Generate response
        """
        if self.graph is None:
            async with self._graph_init_lock:
                # Double-check pattern: another coroutine might have initialized it
                if self.graph is None:
                    # Initialize checkpointer
                    await self._initialize_checkpointer()

                    # Create runtime context with all dependencies
                    from soni.core.state import create_runtime_context
                    from soni.dm.orchestrator import build_orchestrator_graph

                    runtime_context = create_runtime_context(
                        config=self.config,
                        scope_manager=self.scope_manager,
                        normalizer=self.normalizer,
                        action_handler=self.action_handler,
                        du=self.du,
                    )

                    # Build orchestrator graph with flow subgraphs
                    self.graph = build_orchestrator_graph(
                        config=self.config,
                        context=runtime_context,
                        checkpointer=self.checkpointer,
                    )

                    # Store runtime context for reference
                    self._runtime_context = runtime_context

                    # Initialize managers after graph is built
                    self.conversation_manager = ConversationManager(self.graph)
                    self.streaming_manager = StreamingManager()

    async def _initialize_checkpointer(self) -> None:
        """Initialize the checkpointer asynchronously."""
        if self.checkpointer is None:
            self.checkpointer, self._checkpointer_cm = await CheckpointerFactory.create(
                self.config.settings.persistence
            )

    async def _cleanup_checkpointer(self) -> None:
        """Cleanup checkpointer resources."""
        if self._checkpointer_cm is not None:
            try:
                # Close the async context manager to release resources
                await self._checkpointer_cm.__aexit__(None, None, None)
                logger.debug("Checkpointer context manager closed successfully")
            except (OSError, ConnectionError, RuntimeError) as e:
                logger.warning(
                    f"Error closing checkpointer context manager: {e}",
                    extra={"error_type": type(e).__name__},
                )
            except Exception as e:
                logger.error(
                    f"Unexpected error closing checkpointer: {e}",
                    exc_info=True,
                )
            finally:
                # Clear references immediately
                self._checkpointer_cm = None
                self.checkpointer = None
                import gc

                gc.collect()
        elif self.checkpointer is not None:
            # No context manager (e.g., InMemorySaver) - just clear reference
            self.checkpointer = None

    async def cleanup(self) -> None:
        """Cleanup resources, especially the graph builder's checkpointer.

        Should be called when the RuntimeLoop is no longer needed to ensure
        proper resource cleanup. Idempotent - safe to call multiple times.
        """
        if not self._cleaned_up:
            await self._cleanup_checkpointer()
            logger.info("RuntimeLoop cleanup completed")
            self._cleaned_up = True

    def __del__(self) -> None:
        """Destructor to ensure cleanup is called when object is garbage collected.

        Note: Relying on __del__ is not ideal, but provides a safety net.
        Since cleanup() is now async, __del__ cannot call it directly.
        Explicit cleanup() calls are preferred.
        """
        # Note: Cannot call async cleanup() from __del__
        # Resources will be cleaned up when context manager exits
        pass

    def _validate_inputs(self, user_msg: str, user_id: str) -> tuple[str, str]:
        """Validate and sanitize input parameters for message processing.

        Validates that user message and user ID are non-empty strings and sanitizes them
        to prevent injection attacks and DoS. Logs validation success with message preview and length.

        Args:
            user_msg: User's input message (must be non-empty after stripping)
            user_id: Unique identifier for user/conversation (must be non-empty after stripping)

        Returns:
            Tuple of (sanitized_user_msg, sanitized_user_id)

        Raises:
            ValidationError: If user_msg is empty or invalid after sanitization
            ValidationError: If user_id is empty or invalid after sanitization

        Example:
            >>> runtime._validate_inputs("Hello", "user123")
            ("Hello", "user123")

            >>> runtime._validate_inputs("", "user123")
            ValidationError: User message cannot be empty

        Note:
            This method logs the validation success with structured logging,
            including user_id and message length for debugging and monitoring.
            All inputs are sanitized to prevent security vulnerabilities.
        """
        # Sanitize user message (removes dangerous patterns, validates length)
        sanitized_msg = sanitize_user_message(user_msg)

        # Sanitize user ID (validates format, length)
        sanitized_user_id = sanitize_user_id(user_id)

        logger.info(
            f"Processing message for user {sanitized_user_id}: {sanitized_msg[:50]}...",
            extra={
                "user_id": sanitized_user_id,
                "message_length": len(sanitized_msg),
            },
        )

        return sanitized_msg, sanitized_user_id

    async def _load_or_create_state(self, user_id: str, user_msg: str) -> DialogueState:
        """Load existing state from checkpoint or create new state.

        Args:
            user_id: Unique identifier for the user
            user_msg: The user's message (for new state initialization)

        Returns:
            DialogueState instance (loaded or newly created)

        Raises:
            RuntimeError: If state loading fails unexpectedly
        """
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
            if self.checkpointer:
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
            # Note: snapshot.values might be a partial state update from LangGraph
            # We need to handle this gracefully
            # Load existing state from checkpoint (allow partial to handle incomplete snapshots)
            state = state_from_dict(existing_state_snapshot.values, allow_partial=True)
            # Update user_message field (per design: understand_node reads from here)
            state["user_message"] = user_msg
            add_message(state, "user", user_msg)
            all_slots = get_all_slots(state)
            logger.debug(
                f"Updated existing state: {len(state['messages'])} messages, "
                f"{len(all_slots)} slots, turn {state['turn_count']}"
            )
        else:
            # Create new state with new schema
            state = create_initial_state(user_msg)
            logger.debug("Created new state for new conversation")

        return state

    async def _execute_graph(
        self,
        state: DialogueState,
        user_id: str,
    ) -> dict[str, Any]:
        """
        Execute LangGraph with the given state.

        Args:
            state: Current dialogue state
            user_id: Unique identifier for the user

        Returns:
            Graph execution result (final state dict)

        Raises:
            NLUError: If NLU processing fails
            ValidationError: If validation fails
            ActionNotFoundError: If action not found
            SoniError: If graph execution fails unexpectedly
        """
        # Get scoped actions based on current state
        # Note: state.config hack removed - nodes now use RuntimeContext
        scoped_actions = self.scope_manager.get_available_actions(state)
        logger.debug(
            f"Scoped actions for user {user_id}: {scoped_actions} (total: {len(scoped_actions)})"
        )

        # Log scoping metrics
        total_actions = len(self.config.actions) if hasattr(self.config, "actions") else 0
        scoped_count = len(scoped_actions)
        current_flow = get_current_flow(state)
        if total_actions > 0:
            reduction = (
                ((total_actions - scoped_count) / total_actions * 100) if total_actions > 0 else 0
            )
            logger.info(
                f"Action scoping for user {user_id}: "
                f"{scoped_count}/{total_actions} actions ({reduction:.1f}% reduction)",
                extra={
                    "user_id": user_id,
                    "total_actions": total_actions,
                    "scoped_actions": scoped_count,
                    "reduction_percent": reduction,
                    "current_flow": current_flow,
                },
            )

        # Execute graph
        config = {"configurable": {"thread_id": user_id}}

        # Check if graph is interrupted (has pending nodes)
        snapshot = await self.graph.aget_state(config)

        # Check if graph is interrupted (has pending tasks)
        # StateSnapshot has 'next' attribute (tuple of pending node names)
        # Empty tuple () means no pending tasks
        if snapshot and hasattr(snapshot, "next") and snapshot.next:
            # Graph is interrupted - resume with user message
            # Use Command(resume=msg) to pass user input to interrupt()
            from langgraph.types import Command

            result_raw = await self.graph.ainvoke(
                Command(resume=state["user_message"]),
                config=config,
            )
        else:
            # New or completed conversation - start from beginning
            result_raw = await self.graph.ainvoke(
                state_to_dict(state),
                config=config,
            )

        # Type assertion: graph.ainvoke returns dict-like state
        result: dict[str, Any] = dict(result_raw) if isinstance(result_raw, dict) else {}

        # Check if graph is still interrupted AFTER execution
        # If interrupted, process interrupts to extract prompt
        # If completed, use last_response from nodes (e.g., generate_response_node)
        post_execution_snapshot = await self.graph.aget_state(config)
        is_still_interrupted = (
            post_execution_snapshot
            and hasattr(post_execution_snapshot, "next")
            and post_execution_snapshot.next
        )

        # Check if we have a last_response from nodes (e.g., generate_response_node)
        # This takes priority over interrupts
        has_last_response_from_nodes = bool(result.get("last_response"))

        logger.info(
            f"After graph execution: is_still_interrupted={is_still_interrupted}, "
            f"last_response_before_interrupts={result.get('last_response')}, "
            f"has_interrupt={('__interrupt__' in result)}, "
            f"has_last_response_from_nodes={has_last_response_from_nodes}"
        )

        # CRITICAL: When graph is interrupted, ALWAYS process interrupts to extract the prompt
        # even if there's a last_response from previous state. The interrupt value takes priority
        # because it represents the NEW prompt from the interrupting node (e.g., collect_next_slot,
        # confirm_action). The existing last_response is from a previous turn and should be replaced.
        if is_still_interrupted:
            # Graph is interrupted - process interrupts to extract the new prompt
            logger.info("Graph interrupted, processing interrupts to extract new prompt")
            self._process_interrupts(result)
            logger.info(f"After processing interrupts, last_response={result.get('last_response')}")
        elif has_last_response_from_nodes:
            # We have a response from nodes (e.g., generate_response_node) - use it
            # Don't process interrupts as they would overwrite the final response
            logger.info(f"Using last_response from nodes: {result.get('last_response')}")
        else:
            # Graph completed but no response - process interrupts as fallback
            logger.warning(
                "Graph completed but no last_response, processing interrupts as fallback"
            )
            self._process_interrupts(result)

        logger.info(
            f"Graph execution completed for user {user_id}",
            extra={
                "user_id": user_id,
                "turn_count": state["turn_count"] + 1,
                "current_flow": result.get("current_flow"),
                "final_last_response": result.get("last_response"),
            },
        )

        return result

    def _process_interrupts(self, result: dict[str, Any]) -> None:
        """
        Process interrupt values and update state accordingly.

        When a graph is interrupted, LangGraph includes an '__interrupt__' key
        in the result with Interrupt objects containing the interrupt values.
        This method extracts relevant information from interrupts and updates
        the result state (e.g., setting last_response to the prompt).

        Args:
            result: Graph execution result dict (modified in-place)

        Note:
            This follows SRP by separating interrupt handling from graph execution.
            According to LangGraph docs (v0.4.0+), result["__interrupt__"] contains
            a list of Interrupt objects with value, resumable, and ns attributes.
        """
        if "__interrupt__" not in result or not result["__interrupt__"]:
            return

        interrupts = result["__interrupt__"]
        if not interrupts or len(interrupts) == 0:
            return

        # Extract the first interrupt (typically only one for our use case)
        first_interrupt = interrupts[0]

        # Extract the prompt value from the interrupt
        # The interrupt can be an object with .value attribute or a dict
        prompt = None
        if hasattr(first_interrupt, "value"):
            prompt = first_interrupt.value
        elif isinstance(first_interrupt, dict) and "value" in first_interrupt:
            prompt = first_interrupt["value"]

        # If the interrupt value is a string, treat it as a prompt
        # and set it as last_response so the user sees it
        if prompt and isinstance(prompt, str):
            result["last_response"] = prompt
            logger.info(
                "Extracted prompt from interrupt",
                extra={
                    "prompt_preview": prompt[:50] + ("..." if len(prompt) > 50 else ""),
                    "prompt_length": len(prompt),
                },
            )

    def _extract_response(
        self,
        result: dict[str, Any],
        user_id: str,
    ) -> str:
        """
        Extract response message from graph execution result.

        Extracts the 'last_response' field from the final state dictionary
        returned by the graph execution. If not present, returns a default
        fallback message.

        Args:
            result: Graph execution result dictionary containing final state
                (should have 'last_response' key set by graph nodes)
            user_id: Unique identifier for the user (for logging)

        Returns:
            Response message string (never empty, always has fallback)

        Example:
            >>> result = {"last_response": "Flight booked successfully!"}
            >>> runtime._extract_response(result, "user123")
            'Flight booked successfully!'

            >>> result = {}  # No response set
            >>> runtime._extract_response(result, "user123")
            "I'm sorry, I didn't understand that."

        Note:
            - Always returns a non-empty string (fallback if missing)
            - Logs successful extraction with response length
            - The 'last_response' field is set by graph nodes (collect, action, etc.)
        """
        # Extract response from result
        # The graph should update state with last_response
        response_raw = result.get("last_response")

        # If last_response is the prompt from interrupt, use it
        if response_raw:
            response = str(response_raw)
        else:
            response = "I'm sorry, I didn't understand that."

        logger.info(
            f"Successfully processed message for user {user_id}",
            extra={
                "user_id": user_id,
                "response_length": len(response),
            },
        )

        return response

    async def process_message(
        self,
        user_msg: str,
        user_id: str,
    ) -> str:
        """
        Process a user message and return response.

        High-level orchestrator that delegates to helper methods.
        Each step is separated for clarity and testability.

        Args:
            user_msg: User's input message
            user_id: Unique identifier for user/conversation

        Returns:
            Response message from the dialogue system

        Raises:
            ValidationError: If inputs are invalid
            NLUError: If NLU processing fails
            ActionNotFoundError: If action not found
            SoniError: If processing fails
        """
        try:
            # 1. Validate and sanitize inputs
            sanitized_msg, sanitized_user_id = self._validate_inputs(user_msg, user_id)

            # 2. Ensure graph is initialized (lazy initialization)
            await self._ensure_graph_initialized()

            # 3. Load or create state (use sanitized values)
            state = await self._load_or_create_state(sanitized_user_id, sanitized_msg)

            # 4. Execute graph (use sanitized user_id)
            result = await self._execute_graph(state, sanitized_user_id)

            # 5. Extract and return response
            return self._extract_response(result, sanitized_user_id)

        except ValidationError as e:
            # Use original user_id for logging (before sanitization)
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
        # Validate and sanitize inputs
        sanitized_msg, sanitized_user_id = self._validate_inputs(user_msg, user_id)

        logger.info(
            f"Processing message stream for user {sanitized_user_id}: {sanitized_msg[:50]}..."
        )
        start_time = time.time()
        first_token_sent = False

        try:
            # Ensure graph is initialized (lazy initialization)
            await self._ensure_graph_initialized()

            # Get or create state using ConversationManager (use sanitized values)
            if self.conversation_manager is None:
                raise SoniError("ConversationManager not initialized")
            state = await self.conversation_manager.get_or_create_state(sanitized_user_id)
            add_message(state, "user", sanitized_msg)

            # Get scoped actions based on current state
            scoped_actions = self.scope_manager.get_available_actions(state)
            logger.debug(
                f"Scoped actions for user {sanitized_user_id}: {scoped_actions} "
                f"(total: {len(scoped_actions)})"
            )

            # Stream graph execution using StreamingManager (use sanitized user_id)
            if self.streaming_manager is None:
                raise SoniError("StreamingManager not initialized")
            async for event in self.streaming_manager.stream_response(
                graph=self.graph,
                state=state,
                user_id=sanitized_user_id,
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
                                            f"First token latency for user {sanitized_user_id}: "
                                            f"{first_token_latency:.2f}ms"
                                        )
                                        first_token_sent = True

                                    # Yield token (SSE format will be handled by endpoint)
                                    yield token + " "

                                # Yield final newline to signal completion of this chunk
                                yield "\n"

            # State is automatically saved by checkpointing
            logger.info(f"Successfully processed message stream for user {sanitized_user_id}")

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
