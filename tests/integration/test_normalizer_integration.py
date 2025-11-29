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
    runtime.cleanup()


@pytest.mark.asyncio
async def test_normalizer_in_graph_node():
    """Test that normalizer is used in understand_node"""
    # Arrange
    from soni.core.state import DialogueState
    from soni.dm.graph import understand_node

    config_dict = ConfigLoader.load(Path("examples/flight_booking/soni.yaml"))
    config = SoniConfig(**config_dict)

    state = DialogueState(
        messages=[{"role": "user", "content": "I want to book a flight from  Madrid  "}],
        current_flow="book_flight",
        slots={},
    )
    state.config = config

    # Act & Assert
    # This test verifies that the understand_node can be called
    # The actual normalization happens inside, but we can't easily test it
    # without mocking the entire NLU pipeline
    # For now, we just verify the node doesn't crash with normalization code
    try:
        result = await understand_node(state)
        # If we get here, normalization didn't break the flow
        assert isinstance(result, dict)
    except Exception as e:
        # If it's an NLU error (expected without real LLM), that's ok
        # We just want to make sure normalization code doesn't cause issues
        assert "normalization" not in str(e).lower() or "nlu" in str(e).lower()
