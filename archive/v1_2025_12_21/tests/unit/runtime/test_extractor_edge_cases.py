"""Edge case tests for ResponseExtractor.

Tests handling of empty, multiple, and malformed messages.
"""

import pytest
from langchain_core.messages import AIMessage, HumanMessage
from soni.runtime.extractor import ResponseExtractor


class TestResponseExtractorEdgeCases:
    """Edge case tests for ResponseExtractor."""

    @pytest.fixture
    def extractor(self):
        return ResponseExtractor()

    def test_extract_with_no_new_messages(self, extractor):
        """Test extraction when no new messages added."""
        history = [HumanMessage(content="hello")]
        result = {"messages": [HumanMessage(content="hello")]}  # Same as history
        input_payload = {"messages": [HumanMessage(content="hello")]}

        response = extractor.extract(result, input_payload, history)

        # Should handle gracefully, return empty or default
        assert isinstance(response, str)

    def test_extract_with_empty_ai_message(self, extractor):
        """Test extraction when AI message has empty content."""
        history: list = []
        result = {
            "messages": [
                HumanMessage(content="hello"),
                AIMessage(content=""),  # Empty content
            ]
        }
        input_payload = {"messages": [HumanMessage(content="hello")]}

        response = extractor.extract(result, input_payload, history)

        # Should not fail, may return empty or fallback
        assert isinstance(response, str)

    def test_extract_with_multiple_ai_messages(self, extractor):
        """Test extraction when multiple AI messages generated."""
        history: list = []
        result = {
            "messages": [
                HumanMessage(content="hello"),
                AIMessage(content="First response"),
                AIMessage(content="Second response"),
            ]
        }
        input_payload = {"messages": [HumanMessage(content="hello")]}

        response = extractor.extract(result, input_payload, history)

        # Should combine or use last
        assert isinstance(response, str)
        assert len(response) > 0

    def test_extract_with_mixed_message_types(self, extractor):
        """Test extraction with mixed message types."""
        history: list = []
        result = {
            "messages": [
                HumanMessage(content="hello"),
                AIMessage(content="AI response"),
                HumanMessage(content="follow-up"),
            ]
        }
        input_payload = {"messages": [HumanMessage(content="hello")]}

        response = extractor.extract(result, input_payload, history)

        # Should at minimum include AI message
        assert "AI response" in response

    def test_extract_handles_messages_already_in_history(self, extractor):
        """Test that messages in history are not re-extracted."""
        ai_msg = AIMessage(content="previous response")
        history = [HumanMessage(content="hello"), ai_msg]
        result = {
            "messages": [
                HumanMessage(content="hello"),
                ai_msg,  # Same object as in history
                AIMessage(content="new response"),
            ]
        }
        input_payload = {"messages": [HumanMessage(content="hello")]}

        response = extractor.extract(result, input_payload, history)

        # Should only extract new messages
        assert "new response" in response

    def test_extract_with_only_human_messages(self, extractor):
        """Test extraction when result has only human messages."""
        history: list = []
        result = {
            "messages": [
                HumanMessage(content="hello"),
                HumanMessage(content="world"),
            ]
        }
        input_payload = {"messages": [HumanMessage(content="hello")]}

        response = extractor.extract(result, input_payload, history)

        # Should handle gracefully
        assert isinstance(response, str)
