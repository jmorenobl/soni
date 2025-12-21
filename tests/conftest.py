"""Shared fixtures for Soni tests."""

import pytest

# Configure DSPy for all tests
import dspy

# Use a fast, cheap model for tests
# Requires OPENAI_API_KEY environment variable
lm = dspy.LM("openai/gpt-4o-mini")
dspy.configure(lm=lm)
@pytest.fixture
def empty_dialogue_state():
    """Create an empty dialogue state for testing."""
    from soni.core.state import create_empty_dialogue_state

    return create_empty_dialogue_state()


@pytest.fixture
def mock_runtime():
    """Create a mock Runtime[RuntimeContext] for testing nodes."""
    from unittest.mock import AsyncMock, MagicMock

    from langgraph.runtime import Runtime

    from soni.config import SoniConfig
    from soni.core.types import RuntimeContext

    mock_context = MagicMock(spec=RuntimeContext)
    mock_context.flow_manager = MagicMock()
    mock_context.du = AsyncMock()
    mock_context.action_handler = AsyncMock()
    # Use real minimal config to pass Pydantic validation
    mock_context.config = SoniConfig(flows={}, slots={})
    mock_context.slot_extractor = None

    # We can mock Runtime using MagicMock for simplicty since we just need .context access
    # But creating real Runtime is better for type checking simulation
    runtime = Runtime(
        context=mock_context,
        store=None,
        stream_writer=lambda x: None,
        previous=None,
    )
    return runtime
