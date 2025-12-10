"""Integration tests for Dialogue Understanding module with real LLM."""

import pytest

from soni.du.modules import SoniDU


@pytest.mark.integration
@pytest.mark.asyncio
def test_soni_du_integration_real_dspy(configure_dspy_for_integration, skip_without_api_key):
    """
    Integration test with real DSPy LM (requires API key).

    This test runs with integration tests: make test-integration

    Requires OPENAI_API_KEY environment variable.
    """
    # Arrange
    du = SoniDU()

    # Act
    result = du.forward(
        user_message="I want to book a flight to Paris",
        dialogue_history="",
        current_slots="{}",
        available_actions='["book_flight", "search_flights", "help"]',
        available_flows='{"book_flight": "Book a flight"}',
        current_flow="none",
    )

    # Assert
    assert result is not None
    assert hasattr(result, "structured_command")
    assert hasattr(result, "extracted_slots")
    assert result.structured_command is not None
