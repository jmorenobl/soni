"""Runtime loop for Soni Framework"""

import logging
from pathlib import Path

from soni.core.config import ConfigLoader, SoniConfig
from soni.core.errors import SoniError, ValidationError
from soni.core.state import DialogueState
from soni.dm.graph import SoniGraphBuilder
from soni.du.modules import SoniDU

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
    ) -> None:
        """
        Initialize RuntimeLoop with configuration.

        Args:
            config_path: Path to YAML configuration file
            optimized_du_path: Optional path to optimized SoniDU module (JSON)
        """
        # Load configuration
        config_dict = ConfigLoader.load(config_path)
        self.config = SoniConfig(**config_dict)

        # Build graph
        self.builder = SoniGraphBuilder(self.config)
        # Use first flow for MVP
        flow_name = list(self.config.flows.keys())[0]
        self.graph = self.builder.build_manual(flow_name=flow_name)

        # Initialize DU module
        if optimized_du_path and Path(optimized_du_path).exists():
            from soni.du.optimizers import load_optimized_module

            self.du = load_optimized_module(optimized_du_path)
            logger.info(f"Loaded optimized DU from {optimized_du_path}")
        else:
            self.du = SoniDU()
            logger.info("Using default (non-optimized) DU module")

        logger.info(f"RuntimeLoop initialized with config: {config_path}")

    def cleanup(self) -> None:
        """
        Cleanup resources, especially the graph builder's checkpointer.

        Should be called when the RuntimeLoop is no longer needed to ensure
        proper resource cleanup.
        """
        if hasattr(self, "builder") and self.builder:
            self.builder.cleanup()
            logger.info("RuntimeLoop cleanup completed")

    def __del__(self) -> None:
        """
        Destructor to ensure cleanup is called when object is garbage collected.

        Note: Relying on __del__ is not ideal, but provides a safety net.
        Explicit cleanup() calls are preferred.
        """
        self.cleanup()

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
            # Configure checkpointing with thread_id = user_id
            config = {
                "configurable": {
                    "thread_id": user_id,
                }
            }

            # Try to load existing state from checkpoint
            existing_state_snapshot = None
            try:
                # Use get_state() to retrieve the current checkpoint for this thread
                if self.builder.checkpointer:
                    existing_state_snapshot = self.graph.get_state(config)
                    if existing_state_snapshot and existing_state_snapshot.values:
                        logger.info(f"Loaded existing state for user {user_id}")
                    else:
                        logger.info(f"No existing state found for user {user_id}, creating new")
            except Exception as e:
                # No existing state or error loading, create new
                logger.warning(f"Could not load checkpoint for user {user_id}: {e}")
                existing_state_snapshot = None

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

            # Inject config into state for node access
            # Note: This is a workaround for MVP
            state.config = self.config  # type: ignore[attr-defined]

            # Execute graph
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
        except Exception as e:
            logger.error(
                f"Unexpected error processing message for user {user_id}: {e}",
                exc_info=True,
            )
            raise SoniError(f"Failed to process message: {e}") from e
