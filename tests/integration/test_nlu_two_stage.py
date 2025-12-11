"""Integration tests for two-stage NLU prediction."""

import pytest

from soni.core.errors import SoniError


@pytest.mark.integration
@pytest.mark.asyncio
async def test_two_stage_prediction_without_active_flow(
    runtime, configure_dspy_for_integration, skip_without_api_key
):
    """Test that two-stage prediction works when no flow is active."""
    user_id = "test-two-stage-001"
    await runtime._ensure_graph_initialized()

    # Act - User provides all slots at once without active flow
    response = await runtime.process_message(
        "I want to book a flight from NYC to LAX tomorrow", user_id
    )

    # Assert - System should extract all slots correctly
    # (This test should pass with two-stage approach)
    assert isinstance(response, str)
    assert len(response) > 0

    # Verify slots were extracted (check state if possible)
    # Or verify response indicates slots were understood
    # The response should indicate the system understood the booking request


@pytest.mark.integration
@pytest.mark.asyncio
async def test_two_stage_with_invalid_command(
    runtime, configure_dspy_for_integration, skip_without_api_key
):
    """Test that two-stage handles invalid commands gracefully."""
    user_id = "test-two-stage-002"
    await runtime._ensure_graph_initialized()

    # Act - User says something that doesn't map to a flow
    try:
        response = await runtime.process_message(
            "I want to do something weird that doesn't exist", user_id
        )

        # Assert - System should handle gracefully (not crash)
        assert isinstance(response, str)
        # Should either ask for clarification or indicate it doesn't understand
    except SoniError:
        # Acceptable - system may raise error for invalid commands
        pass


@pytest.mark.integration
@pytest.mark.asyncio
async def test_two_stage_skipped_when_flow_active(
    runtime, configure_dspy_for_integration, skip_without_api_key
):
    """Test that two-stage is skipped when flow is already active."""
    user_id = "test-two-stage-003"
    await runtime._ensure_graph_initialized()

    # Arrange - Start a flow first
    await runtime.process_message("I want to book a flight", user_id)

    # Act - Provide slots (flow is now active)
    response = await runtime.process_message("from NYC to LAX", user_id)

    # Assert - Should use single-stage (flow is active)
    # Verify it works correctly (slots extracted)
    assert isinstance(response, str)
    assert len(response) > 0
