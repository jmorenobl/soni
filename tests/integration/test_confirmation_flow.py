"""Integration tests for confirmation flow."""

from pathlib import Path

import pytest

from soni.runtime import RuntimeLoop


@pytest.fixture
async def runtime():
    """Create runtime for testing.

    RuntimeLoop automatically imports actions from config directory
    via _auto_import_actions and _try_import_config_package.
    """
    config_path = Path("examples/flight_booking/soni.yaml")
    runtime = RuntimeLoop(config_path)
    runtime.config.settings.persistence.backend = "memory"
    await runtime._ensure_graph_initialized()
    yield runtime
    await runtime.cleanup()


# === HAPPY PATH ===
@pytest.mark.integration
@pytest.mark.asyncio
async def test_action_to_confirmation_flow(
    runtime, configure_dspy_for_integration, skip_without_api_key
):
    """Test that after action execution, system displays confirmation message."""
    user_id = "test_confirmation_flow"

    # Act - Complete flow up to confirmation
    await runtime.process_message("I want to book a flight", user_id)
    await runtime.process_message("Madrid", user_id)
    await runtime.process_message("Barcelona", user_id)
    response = await runtime.process_message("Tomorrow", user_id)

    # Get state
    config = {"configurable": {"thread_id": user_id}}
    snapshot = await runtime.graph.aget_state(config)
    state = snapshot.values

    # Assert
    # Check that we're at confirmation step
    flow_stack = state.get("flow_stack", [])
    assert len(flow_stack) > 0
    active_ctx = flow_stack[-1]
    assert active_ctx["current_step"] == "ask_confirmation"

    # Check conversation_state
    conv_state = state.get("conversation_state")
    assert conv_state in ("ready_for_confirmation", "confirming")

    # Check response contains confirmation message
    assert "flight" in response.lower() or "Madrid" in response or "Barcelona" in response
    # Should NOT be default response
    assert response != "How can I help you?"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_confirmation_message_includes_slots(
    runtime, configure_dspy_for_integration, skip_without_api_key
):
    """Test that confirmation message includes interpolated slot values."""
    user_id = "test_confirmation_message"

    # Act
    await runtime.process_message("I want to book a flight", user_id)
    await runtime.process_message("New York", user_id)
    await runtime.process_message("Los Angeles", user_id)
    response = await runtime.process_message("2025-12-15", user_id)

    # Assert - Confirmation message should include slot values
    assert "New York" in response or "Los Angeles" in response
    assert "confirm" in response.lower() or "correct" in response.lower()


@pytest.mark.integration
@pytest.mark.asyncio
async def test_complete_confirmation_flow_yes(
    runtime, configure_dspy_for_integration, skip_without_api_key
):
    """Test complete flow: book flight, confirm with yes, complete booking."""
    user_id = "test_complete_yes"

    # Step 1: Start flow
    response = await runtime.process_message("I want to book a flight", user_id)
    assert "depart" in response.lower() or "origin" in response.lower()

    # Step 2-4: Provide slots
    await runtime.process_message("Madrid", user_id)
    await runtime.process_message("Barcelona", user_id)
    response = await runtime.process_message("Tomorrow", user_id)

    # Should show confirmation message
    assert "Madrid" in response or "Barcelona" in response
    assert "confirm" in response.lower()

    # Step 5: Confirm
    response = await runtime.process_message("Yes, please confirm", user_id)

    # Should complete booking
    assert (
        "booking" in response.lower()
        or "confirmed" in response.lower()
        or "reference" in response.lower()
    )


@pytest.mark.integration
@pytest.mark.asyncio
async def test_complete_confirmation_flow_no_then_modify(
    runtime, configure_dspy_for_integration, skip_without_api_key
):
    """Test flow: book flight, deny confirmation, modify slot, confirm again."""
    user_id = "test_deny_modify"

    # Steps 1-4: Complete to confirmation
    await runtime.process_message("I want to book a flight", user_id)
    await runtime.process_message("New York", user_id)
    await runtime.process_message("Los Angeles", user_id)
    response = await runtime.process_message("2025-12-15", user_id)

    # Should show confirmation
    assert "New York" in response or "Los Angeles" in response
    assert "confirm" in response.lower()

    # Deny confirmation
    response = await runtime.process_message("No, change the destination", user_id)

    # Should ask what to change
    assert "change" in response.lower() or "modify" in response.lower()

    # Modify destination
    response = await runtime.process_message("San Francisco", user_id)

    # Should show updated confirmation or continue flow
    assert "San Francisco" in response or "confirm" in response.lower()


@pytest.mark.integration
@pytest.mark.asyncio
async def test_confirmation_unclear_then_yes(
    runtime, configure_dspy_for_integration, skip_without_api_key
):
    """Test flow: unclear response, retry, then yes."""
    user_id = "test_unclear"

    # Complete to confirmation
    await runtime.process_message("Book a flight", user_id)
    await runtime.process_message("Boston", user_id)
    await runtime.process_message("Seattle", user_id)
    await runtime.process_message("Next week", user_id)

    # Unclear response
    response = await runtime.process_message("hmm, I'm not sure", user_id)

    # Should ask again
    assert "understand" in response.lower() or "yes" in response.lower() or "no" in response.lower()

    # Now confirm clearly
    response = await runtime.process_message("Yes, that's correct", user_id)

    # Should complete
    assert "booking" in response.lower() or "confirmed" in response.lower()


@pytest.mark.integration
@pytest.mark.asyncio
async def test_confirmation_max_retries(
    runtime, configure_dspy_for_integration, skip_without_api_key
):
    """Test that max retries trigger error state."""
    user_id = "test_max_retries"

    # Complete to confirmation
    await runtime.process_message("Book a flight", user_id)
    await runtime.process_message("Chicago", user_id)
    await runtime.process_message("Denver", user_id)
    await runtime.process_message("2025-12-20", user_id)

    # Give unclear responses 3 times
    response1 = await runtime.process_message("maybe", user_id)
    assert "understand" in response1.lower()

    response2 = await runtime.process_message("hmm", user_id)
    assert "understand" in response2.lower()

    response3 = await runtime.process_message("I don't know", user_id)

    # After 3 unclear responses, should error or reset
    assert "trouble" in response3.lower() or "start over" in response3.lower()
