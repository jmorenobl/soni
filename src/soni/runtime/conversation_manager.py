"""Conversation state management for multi-user dialogues"""

import logging
from typing import Any

from soni.core.state import (
    DialogueState,
    create_empty_state,
    state_from_dict,
    state_to_dict,
)

logger = logging.getLogger(__name__)


class ConversationManager:
    """Manages multi-user conversation state."""

    def __init__(self, graph: Any):
        """
        Initialize ConversationManager.

        Args:
            graph: Compiled LangGraph StateGraph with checkpointer
        """
        self.graph = graph

    async def get_or_create_state(
        self,
        user_id: str,
    ) -> DialogueState:
        """
        Get existing state or create new one.

        Args:
            user_id: Unique identifier for the user/conversation

        Returns:
            DialogueState instance (existing or new)
        """

        config = {"configurable": {"thread_id": user_id}}
        snapshot = await self.graph.aget_state(config)

        if snapshot and snapshot.values:
            # Load existing state (allow partial to handle incomplete snapshots)
            state = state_from_dict(snapshot.values, allow_partial=True)
            logger.debug(f"Loaded existing state for user {user_id}")
            return state
        else:
            logger.debug(f"Creating new state for user {user_id}")
            return create_empty_state()

    async def save_state(
        self,
        user_id: str,
        state: DialogueState,
    ) -> None:
        """
        Save conversation state.

        Args:
            user_id: Unique identifier for the user/conversation
            state: DialogueState to save
        """
        config = {"configurable": {"thread_id": user_id}}
        await self.graph.aupdate_state(config, state_to_dict(state))
        logger.debug(f"Saved state for user {user_id}")
