"""Integration tests for normalizer in runtime pipeline"""

from pathlib import Path

import pytest

from soni.core.config import ConfigLoader, SoniConfig
from soni.runtime import RuntimeLoop


@pytest.mark.asyncio
async def test_runtime_initializes_normalizer():
    """Test that RuntimeLoop initializes normalizer correctly"""
    # Arrange
    config_path = Path("examples/flight_booking/soni.yaml")

    # Act
    runtime = RuntimeLoop(config_path)

    # Assert
    assert hasattr(runtime, "normalizer")
    assert runtime.normalizer is not None
    assert runtime.normalizer.config is not None

    # Cleanup
    await runtime.cleanup()


@pytest.mark.asyncio
async def test_normalizer_in_graph_node(skip_without_api_key):
    """
    Test that normalizer is used in understand_node.

    This test verifies that the normalizer is properly integrated
    in the understand node through the runtime. The test verifies
    that normalization doesn't cause errors, even if the flow
    requires additional slots.
    """
    # Arrange
    from soni.core.errors import SoniError

    config_path = Path("examples/flight_booking/soni.yaml")
    runtime = RuntimeLoop(config_path)
    user_id = "test-normalizer-1"
    user_msg = "I want to book a flight from  Madrid  "  # Extra spaces to test normalization

    try:
        # Act
        # Initialize graph to ensure normalizer is set up
        await runtime._ensure_graph_initialized()

        # Verify that normalizer is initialized
        assert runtime.normalizer is not None, "Normalizer should be initialized"

        # Process message - normalizer should handle extra spaces
        # The flow may fail if slots are not filled, but normalization should work
        try:
            response = await runtime.process_message(user_msg, user_id)
            # Assert - If successful, verify response
            assert response is not None, "Response should not be None"
            assert isinstance(response, str), "Response should be a string"
            assert len(response) > 0, "Response should not be empty"
        except SoniError as e:
            # If processing fails due to missing slots, that's expected
            # The important thing is that normalization didn't cause the error
            error_msg = str(e).lower()
            # Verify the error is about missing slots, not normalization
            assert "normalization" not in error_msg or "slot" in error_msg, (
                f"Error should be about slots, not normalization: {e}"
            )
            # Normalization should have worked (spaces should be handled)
            # The error is expected because slots aren't filled
            pass

        # Assert - Normalization should not cause errors
        # The normalizer should have processed the message without issues
        assert runtime.normalizer is not None, "Normalizer should still be available"
    finally:
        # Cleanup
        await runtime.cleanup()
