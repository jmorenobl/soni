"""Response Extractor - Extracts response from graph execution result.

Extracted from RuntimeLoop to follow Single Responsibility Principle.
Responsible solely for extracting user-facing response from graph output.
"""

from typing import Any


class ResponseExtractor:
    """Extracts response from graph execution result.

    SRP: Sole responsibility is response extraction logic.
    """

    def extract(
        self,
        result: dict[str, Any],
        input_payload: dict[str, Any] | Any,  # Accept TypedDict or dict
        history: list[Any],
    ) -> str:
        """Extract user-facing response from graph execution result.

        Args:
            result: Graph execution output state.
            input_payload: Input payload that was sent to graph.
            history: Pre-execution message history.

        Returns:
            Extracted response string.
        """
        # Strategy: Identify new messages added during this turn
        # Start length = existing history + 1 (for human message we just added)
        start_len = len(history) + 1

        final_messages = result.get("messages", [])
        new_messages = final_messages[start_len:]

        # Return concatenated new AI messages
        if new_messages:
            contents = [str(m.content) for m in new_messages if hasattr(m, "content") and m.content]
            if contents:
                return "\n\n".join(contents)

        # Fallback to last_response field
        last_response = result.get("last_response")
        if last_response:
            return str(last_response)

        # Final fallback: last message content
        if final_messages and hasattr(final_messages[-1], "content"):
            return str(final_messages[-1].content)

        return "I don't understand."
