"""Tests for ResponseStreamExtractor."""


class TestResponseStreamExtractor:
    """Tests for ResponseStreamExtractor."""

    def test_extract_updates_mode_with_last_response(self):
        """Test extraction from updates mode with last_response."""
        from soni.runtime.stream_extractor import ResponseStreamExtractor

        extractor = ResponseStreamExtractor()
        chunk = {"respond": {"last_response": "Hello world!"}}

        result = extractor.extract(chunk, "updates")

        assert result is not None
        assert result.content == "Hello world!"
        assert result.node == "respond"
        assert result.is_final is True

    def test_extract_updates_mode_skips_internal_nodes(self):
        """Test that internal nodes are skipped."""
        from soni.runtime.stream_extractor import ResponseStreamExtractor

        extractor = ResponseStreamExtractor()
        chunk = {"__start__": {"data": "internal"}}

        result = extractor.extract(chunk, "updates")

        assert result is None

    def test_extract_updates_mode_no_response_field(self):
        """Test extraction when no response field present."""
        from soni.runtime.stream_extractor import ResponseStreamExtractor

        extractor = ResponseStreamExtractor()
        chunk = {"understand": {"nlu_result": "parsed"}}

        result = extractor.extract(chunk, "updates")

        assert result is None

    def test_extract_values_mode(self):
        """Test extraction from values mode."""
        from soni.runtime.stream_extractor import ResponseStreamExtractor

        extractor = ResponseStreamExtractor()
        chunk = {"last_response": "Full state response", "other": "data"}

        result = extractor.extract(chunk, "values")

        assert result is not None
        assert result.content == "Full state response"
        assert result.is_final is True

    def test_extract_custom_mode_string(self):
        """Test extraction from custom mode with string."""
        from soni.runtime.stream_extractor import ResponseStreamExtractor

        extractor = ResponseStreamExtractor()
        chunk = "Custom progress update"

        result = extractor.extract(chunk, "custom")

        assert result is not None
        assert result.content == "Custom progress update"
