"""Core interfaces (Protocols) for Soni Framework following SOLID principles"""

from __future__ import annotations
from typing import Protocol, Dict, Any, List, Optional
from typing_extensions import runtime_checkable


@runtime_checkable
class INLUProvider(Protocol):
    """Protocol for Natural Language Understanding providers"""

    async def predict(
        self,
        user_message: str,
        dialogue_history: str = "",
        current_slots: Optional[Dict[str, Any]] = None,
        available_actions: Optional[List[str]] = None,
        current_flow: str = "none",
    ) -> Dict[str, Any]:
        """
        Predict intent, entities, and structured command from user message.

        Args:
            user_message: The user's input message
            dialogue_history: Previous conversation context
            current_slots: Currently filled slots
            available_actions: List of available actions in current context
            current_flow: Current dialogue flow name

        Returns:
            Dictionary with keys:
                - structured_command: User's intent/command
                - extracted_slots: Extracted entities as dict
                - confidence: Confidence score (0.0-1.0)
                - reasoning: Brief reasoning for the extraction
        """
        ...


@runtime_checkable
class IDialogueManager(Protocol):
    """Protocol for Dialogue Management"""

    async def process_turn(
        self,
        user_message: str,
        user_id: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:  # type: ignore[override]
        """
        Process a single dialogue turn.

        Args:
            user_message: User's input message
            user_id: Unique identifier for the user/conversation
            context: Optional additional context

        Returns:
            Dictionary with response and updated state
        """
        ...


@runtime_checkable
class INormalizer(Protocol):
    """Protocol for slot/entity normalization"""

    async def normalize(
        self,
        value: Any,
        entity_config: Dict[str, Any],
    ) -> Any:
        """
        Normalize a slot/entity value.

        Args:
            value: Raw value to normalize
            entity_config: Configuration for the entity type

        Returns:
            Normalized value
        """
        ...


@runtime_checkable
class IScopeManager(Protocol):
    """Protocol for dynamic action scoping"""

    def get_available_actions(
        self,
        state: Any,  # DialogueState - using Any to avoid circular import
    ) -> List[str]:
        """
        Get list of available actions based on current dialogue state.

        Args:
            state: Current dialogue state

        Returns:
            List of action names available in current context
        """
        ...

