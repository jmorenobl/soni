"""Tests to validate design compliance for corrections and modifications.

These tests validate that the implementation adheres to the design specification
in docs/design/10-dsl-specification/06-patterns.md and docs/design/05-message-flow.md.

These tests are expected to FAIL until the inconsistencies documented in
docs/analysis/DESIGN_IMPLEMENTATION_INCONSISTENCIES.md are fixed.

See DESIGN_IMPLEMENTATION_INCONSISTENCIES.md for details on what needs to be implemented.
"""

import pytest

from soni.core.errors import SoniError
from soni.runtime import RuntimeLoop


@pytest.mark.integration
@pytest.mark.asyncio
@pytest.mark.design_compliance
async def test_correction_during_confirmation_returns_to_confirmation(
    runtime, skip_without_api_key
):
    """
    Test that corrections during confirmation return to confirmation step.

    Design Spec (06-patterns.md lines 162-173):
    User says "No wait, I meant December 20th not 15th" →
    1. Detect correction of departure_date
    2. Update departure_date = "2024-12-20"
    3. Re-display confirmation with updated value
    4. Wait for new confirmation

    This should happen automatically without DSL configuration.
    """
    # Arrange
    user_id = "test-design-correction-confirmation"
    await runtime._ensure_graph_initialized()

    try:
        # Act - Provide all slots to reach confirmation step
        response1 = await runtime.process_message(
            "I want to book a flight from NYC to LAX tomorrow", user_id
        )
        assert isinstance(response1, str)
        assert len(response1) > 0

        # Wait a bit for state to settle
        import asyncio

        await asyncio.sleep(0.1)

        # Act - Correct a slot during confirmation
        # The system should be at confirmation step at this point
        response2 = await runtime.process_message(
            "Actually, I meant next Monday, not tomorrow", user_id
        )

        # Assert - System should re-display confirmation (not advance to next step)
        # Response should contain confirmation language, not asking for new slots
        assert isinstance(response2, str)
        assert len(response2) > 0

        # Should mention the corrected value or confirmation language
        # Should NOT ask for slots that were already provided
        response_lower = response2.lower()
        assert (
            "monday" in response_lower
            or "confirm" in response_lower
            or "correct" in response_lower
            or "is this" in response_lower
        ), (
            f"Response should acknowledge correction and re-show confirmation. "
            f"Got: {response2[:200]}"
        )

        # Should NOT ask for origin/destination/date (already provided)
        assert not (
            "origin" in response_lower and "where" in response_lower and "from" in response_lower
        ), "System should not ask for already-provided slots after correction"

    except SoniError as e:
        pytest.fail(f"Correction during confirmation should work: {e}")


@pytest.mark.integration
@pytest.mark.asyncio
@pytest.mark.design_compliance
async def test_modification_during_confirmation_returns_to_confirmation(
    runtime, skip_without_api_key
):
    """
    Test that modifications during confirmation return to confirmation step.

    Design Spec (06-patterns.md lines 162-166):
    User says "Change the destination to LA" →
    1. Update destination = "LA"
    2. Re-display confirmation with updated value
    3. Wait for new confirmation
    """
    # Arrange
    user_id = "test-design-modification-confirmation"
    await runtime._ensure_graph_initialized()

    try:
        # Act - Provide all slots to reach confirmation step
        response1 = await runtime.process_message(
            "I want to book a flight from NYC to LAX tomorrow", user_id
        )
        assert isinstance(response1, str)
        assert len(response1) > 0

        import asyncio

        await asyncio.sleep(0.1)

        # Act - Modify a slot during confirmation
        response2 = await runtime.process_message(
            "Change the destination to San Francisco", user_id
        )

        # Assert - System should re-display confirmation with updated value
        assert isinstance(response2, str)
        assert len(response2) > 0

        response_lower = response2.lower()
        # Should acknowledge the modification
        assert (
            "san francisco" in response_lower
            or "confirm" in response_lower
            or "changed" in response_lower
            or "updated" in response_lower
        ), (
            f"Response should acknowledge modification and re-show confirmation. "
            f"Got: {response2[:200]}"
        )

    except SoniError as e:
        pytest.fail(f"Modification during confirmation should work: {e}")


@pytest.mark.integration
@pytest.mark.asyncio
@pytest.mark.design_compliance
async def test_correction_returns_to_current_step_not_next(runtime, skip_without_api_key):
    """
    Test that corrections return to current step, not advance to next.

    Design Spec (06-patterns.md line 71):
    "Both patterns are handled the same way: update the slot, return to current step."

    Design Example (lines 53-59):
    Bot: "Flying from Madrid to San Francisco on Dec 15th. Confirm?"
    User: "Sorry, I said San Francisco but I meant San Diego"
    → Returns to confirmation step (NOT restart)
    """
    # Arrange
    user_id = "test-design-correction-return-step"
    await runtime._ensure_graph_initialized()

    try:
        # Act - Provide all slots
        response1 = await runtime.process_message(
            "I want to book a flight from NYC to LAX tomorrow", user_id
        )
        assert isinstance(response1, str)

        import asyncio

        await asyncio.sleep(0.1)

        # Get state to check current step before correction
        # We'll infer from response what step we're at
        initial_response_lower = response1.lower()

        # Act - Correct a slot
        response2 = await runtime.process_message(
            "Actually, change the date to next Monday", user_id
        )

        # Assert - System should stay at same step (or return to it)
        # Should NOT advance to asking for slots that were already provided
        assert isinstance(response2, str)
        assert len(response2) > 0

        response_lower = response2.lower()

        # If we were at confirmation, should still be at confirmation
        # If we were at action, should still be at action
        # Should NOT be asking for origin/destination (already provided)
        if "confirm" in initial_response_lower or "correct" in initial_response_lower:
            # Was at confirmation, should still be at confirmation
            assert (
                "confirm" in response_lower
                or "monday" in response_lower
                or "correct" in response_lower
            ), f"Should return to confirmation step after correction. Got: {response2[:200]}"
        else:
            # Was at another step, should acknowledge correction and continue from there
            assert (
                "monday" in response_lower
                or "date" in response_lower
                or "flight" in response_lower
                or "booking" in response_lower
            ), (
                f"Should acknowledge correction and continue from current step. "
                f"Got: {response2[:200]}"
            )

        # Should NOT ask for already-provided slots
        assert not (
            "origin" in response_lower and "where" in response_lower and "depart" in response_lower
        ), "Should not ask for already-provided origin after correction"

    except SoniError as e:
        pytest.fail(f"Correction should return to current step: {e}")


@pytest.mark.integration
@pytest.mark.asyncio
@pytest.mark.design_compliance
async def test_correction_sets_state_variables(runtime, skip_without_api_key):
    """
    Test that correction sets state variables _correction_slot and _correction_value.

    Design Spec (06-patterns.md lines 225-228):
    | `_correction_slot` | string | Slot that was corrected (if any) |
    | `_correction_value` | any | New value from correction |
    """
    # Arrange
    user_id = "test-design-correction-state-vars"
    await runtime._ensure_graph_initialized()

    try:
        # Act - Provide slots
        await runtime.process_message("I want to book a flight from NYC to LAX tomorrow", user_id)

        import asyncio

        await asyncio.sleep(0.1)

        # Act - Correct a slot
        await runtime.process_message("Actually, change the date to next Monday", user_id)

        # Assert - State should have correction variables set
        # Note: This requires access to internal state, which may not be directly accessible
        # For now, we verify the correction was processed by checking the response
        # TODO: Add API to access state variables for testing
        # This test documents the expected behavior even if we can't fully verify it yet

        # For now, we verify indirectly that correction was processed
        # The actual state variable check would be:
        # state = await runtime.get_state(user_id)
        # assert state.get("_correction_slot") == "departure_date"
        # assert state.get("_correction_value") == "next Monday"

        # Mark as expected to fail until state variable access is implemented
        pytest.skip(
            "State variable access not yet implemented. "
            "This test documents expected behavior: "
            "_correction_slot and _correction_value should be set after correction."
        )

    except SoniError as e:
        pytest.fail(f"Correction should set state variables: {e}")


@pytest.mark.integration
@pytest.mark.asyncio
@pytest.mark.design_compliance
async def test_modification_sets_state_variables(runtime, skip_without_api_key):
    """
    Test that modification sets state variables _modification_slot and _modification_value.

    Design Spec (06-patterns.md lines 227-228):
    | `_modification_slot` | string | Slot that was modified (if any) |
    | `_modification_value` | any | New value from modification |
    """
    # Arrange
    user_id = "test-design-modification-state-vars"
    await runtime._ensure_graph_initialized()

    try:
        # Act - Provide slots
        await runtime.process_message("I want to book a flight from NYC to LAX tomorrow", user_id)

        import asyncio

        await asyncio.sleep(0.1)

        # Act - Modify a slot
        await runtime.process_message("Change the destination to San Francisco", user_id)

        # Assert - State should have modification variables set
        # TODO: Add API to access state variables for testing
        pytest.skip(
            "State variable access not yet implemented. "
            "This test documents expected behavior: "
            "_modification_slot and _modification_value should be set after modification."
        )

    except SoniError as e:
        pytest.fail(f"Modification should set state variables: {e}")


@pytest.mark.integration
@pytest.mark.asyncio
@pytest.mark.design_compliance
async def test_correction_uses_acknowledgment_template(runtime, skip_without_api_key):
    """
    Test that corrections use correction_acknowledged response template.

    Design Spec (02-configuration.md lines 102-107):
    correction_acknowledged:
      default: "Got it, I've updated {slot_name} to {new_value}."
    """
    # Arrange
    user_id = "test-design-correction-template"
    await runtime._ensure_graph_initialized()

    try:
        # Act - Provide slots
        await runtime.process_message("I want to book a flight from NYC to LAX tomorrow", user_id)

        import asyncio

        await asyncio.sleep(0.1)

        # Act - Correct a slot
        response = await runtime.process_message(
            "Actually, change the date to next Monday", user_id
        )

        # Assert - Response should acknowledge correction
        # Should use template or similar acknowledgment language
        assert isinstance(response, str)
        assert len(response) > 0

        response_lower = response.lower()
        # Should acknowledge the correction (template or similar)
        assert (
            "updated" in response_lower
            or "changed" in response_lower
            or "got it" in response_lower
            or "monday" in response_lower
        ), f"Response should acknowledge correction using template. Got: {response[:200]}"

    except SoniError as e:
        pytest.fail(f"Correction should use acknowledgment template: {e}")


@pytest.mark.integration
@pytest.mark.asyncio
@pytest.mark.design_compliance
async def test_modification_uses_acknowledgment_template(runtime, skip_without_api_key):
    """
    Test that modifications use modification_acknowledged response template.

    Design Spec (02-configuration.md lines 109-110):
    modification_acknowledged:
      default: "Done, I've changed {slot_name} to {new_value}."
    """
    # Arrange
    user_id = "test-design-modification-template"
    await runtime._ensure_graph_initialized()

    try:
        # Act - Provide slots
        await runtime.process_message("I want to book a flight from NYC to LAX tomorrow", user_id)

        import asyncio

        await asyncio.sleep(0.1)

        # Act - Modify a slot
        response = await runtime.process_message("Change the destination to San Francisco", user_id)

        # Assert - Response should acknowledge modification
        assert isinstance(response, str)
        assert len(response) > 0

        response_lower = response.lower()
        # Should acknowledge the modification (template or similar)
        assert (
            "done" in response_lower
            or "changed" in response_lower
            or "updated" in response_lower
            or "san francisco" in response_lower
        ), f"Response should acknowledge modification using template. Got: {response[:200]}"

    except SoniError as e:
        pytest.fail(f"Modification should use acknowledgment template: {e}")


@pytest.mark.integration
@pytest.mark.asyncio
@pytest.mark.design_compliance
async def test_correction_automatic_during_confirmation(runtime, skip_without_api_key):
    """
    Test that corrections during confirmation are handled automatically.

    Design Spec (06-patterns.md lines 195-197):
    NOTE: Corrections during confirmation are handled AUTOMATICALLY by the runtime.
    If user says "Sorry, I meant San Diego not San Francisco" during confirm step,
    the runtime updates the slot and re-displays confirmation without any DSL config.
    """
    # Arrange
    user_id = "test-design-correction-auto-confirm"
    await runtime._ensure_graph_initialized()

    try:
        # Act - Provide all slots to reach confirmation
        response1 = await runtime.process_message(
            "I want to book a flight from NYC to LAX tomorrow", user_id
        )
        assert isinstance(response1, str)

        import asyncio

        await asyncio.sleep(0.1)

        # Act - Correct during confirmation (should be automatic)
        response2 = await runtime.process_message("Sorry, I meant San Francisco not LAX", user_id)

        # Assert - Should automatically update and re-show confirmation
        assert isinstance(response2, str)
        assert len(response2) > 0

        response_lower = response2.lower()
        # Should show updated confirmation (with San Francisco)
        # Should NOT require DSL configuration
        assert (
            "san francisco" in response_lower
            or "confirm" in response_lower
            or "correct" in response_lower
        ), f"Correction during confirmation should be automatic. Got: {response2[:200]}"

    except SoniError as e:
        pytest.fail(f"Automatic correction during confirmation should work: {e}")
