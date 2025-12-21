from unittest.mock import AsyncMock, MagicMock

import pytest

from soni.du.models import DialogueContext, NLUOutput
from soni.du.modules import SoniDU


@pytest.fixture
def mock_context():
    """Create minimal DialogueContext for testing."""
    return DialogueContext(
        available_flows=[],
        available_commands=[],
        active_flow=None,
        current_slots=[],
        expected_slot=None,
    )


class TestSoniDUErrorHandling:
    """Tests for SoniDU error handling."""

    @pytest.mark.asyncio
    async def test_aforward_returns_empty_on_extractor_error(self, mock_context):
        """Test that NLU errors return empty output, not raise."""
        # Arrange
        du = SoniDU(use_cot=False)
        du.extractor = MagicMock()
        du.extractor.acall = AsyncMock(side_effect=RuntimeError("LLM timeout"))

        # Act
        result = await du.aforward("hello", mock_context)

        # Assert
        assert isinstance(result, NLUOutput)
        assert result.commands == []
        assert result.confidence == 0.0

    @pytest.mark.asyncio
    async def test_aforward_logs_error_on_failure(self, mock_context, caplog):
        """Test that errors are logged for observability."""
        # Arrange
        import logging

        caplog.set_level(logging.ERROR)

        du = SoniDU(use_cot=False)
        du.extractor = MagicMock()
        du.extractor.acall = AsyncMock(side_effect=ValueError("Parse error"))

        # Act
        await du.aforward("hello", mock_context)

        # Assert
        assert "NLU extraction failed" in caplog.text
        assert "Parse error" in caplog.text

    @pytest.mark.asyncio
    async def test_aforward_success_still_works(self, mock_context):
        """Test that normal operation is unaffected."""
        # Arrange
        du = SoniDU(use_cot=False)
        expected_output = NLUOutput(commands=[], confidence=0.9)

        mock_result = MagicMock()
        mock_result.result = expected_output

        du.extractor = MagicMock()
        du.extractor.acall = AsyncMock(return_value=mock_result)

        # Act
        result = await du.aforward("hello", mock_context)

        # Assert
        assert result == expected_output
        assert result.confidence == 0.9
