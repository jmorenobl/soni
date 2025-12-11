"""Response generation utilities following SRP."""

from typing import Any

from soni.core.state import get_all_slots
from soni.core.types import DialogueState


class ResponseGenerator:
    """Generate responses from state (single responsibility).

    This class is responsible ONLY for generating the response text.
    It does NOT manage state transitions or flow cleanup.
    """

    @staticmethod
    def generate_from_priority(state: DialogueState) -> str:
        """Generate response based on priority order.

        Priority:
        1. confirmation slot (from action outputs)
        2. action_result.message
        3. existing last_response
        4. default fallback

        Args:
            state: Current dialogue state

        Returns:
            Response string to display to user
        """
        slots = get_all_slots(state)

        # Priority 1: Confirmation slot (generic)
        if "confirmation" in slots and slots["confirmation"]:
            return str(slots["confirmation"])

        # Priority 2: Action result message
        action_result = state.get("action_result")
        if action_result:
            if isinstance(action_result, dict):
                message = (
                    action_result.get("message")
                    or action_result.get("confirmation")
                    or f"Action completed successfully. Result: {action_result}"
                )
                return str(message)
            else:
                return f"Action completed successfully. Result: {action_result}"

        # Priority 3: Existing response from previous nodes
        existing_response = state.get("last_response", "")
        if existing_response and existing_response.strip():
            return existing_response

        # Priority 4: Default fallback
        return "How can I help you?"

    @staticmethod
    def generate_confirmation(
        slots: dict[str, Any],
        step_config: Any | None,
        config: Any,
    ) -> str:
        """Generate confirmation message with slot values.

        Uses step_config.message template if available, otherwise generates
        default confirmation message listing all slot values.

        Args:
            slots: Dictionary of slot name to value
            step_config: Current step configuration (may be None)
            config: Soni configuration for slot display names

        Returns:
            Confirmation message string

        Examples:
            >>> slots = {"origin": "NYC", "destination": "LAX"}
            >>> msg = ResponseGenerator.generate_confirmation(slots, None, config)
            >>> print(msg)
            Let me confirm:
            - Origin: NYC
            - Destination: LAX

            Is this correct?
        """
        # Try to use template from step config if available
        if step_config and hasattr(step_config, "message") and step_config.message:
            message_str = str(step_config.message)
            # Interpolate slot values in template
            for slot_name, value in slots.items():
                message_str = message_str.replace(f"{{{slot_name}}}", str(value))
            return message_str

        # Default confirmation message
        message = "Let me confirm:\n"
        for slot_name, value in slots.items():
            # Get display name from slot config if available
            display_name = slot_name
            if hasattr(config, "slots") and config.slots:
                slot_config = config.slots.get(slot_name, {})
                if isinstance(slot_config, dict):
                    display_name = slot_config.get("display_name", slot_name)
            message += f"- {display_name}: {value}\n"
        message += "\nIs this correct?"

        return message

    @staticmethod
    def generate_digression(command: str) -> str:
        """Generate response for digression (question/help).

        Args:
            command: The digression command/question

        Returns:
            Digression response string that always includes words like "question", "help", or "understand"
        """
        if not command:
            return "I understand you have a question. How can I help you with that?"

        return f"I understand you're asking about {command}. Let me help you with that."
