"""Shared fixtures for Soni tests.

Mocks are now in tests/mocks.py.
Patching is handled in tests/unit/conftest.py and tests/integration/conftest.py.
"""

import pytest


@pytest.fixture
def empty_dialogue_state():
    """Create an empty dialogue state for testing."""
    from soni.core.state import create_empty_state

    return create_empty_state()


@pytest.fixture
def mock_runtime():
    """Create a mock Runtime[RuntimeContext] for testing nodes."""
    from unittest.mock import AsyncMock, MagicMock

    from langgraph.runtime import Runtime

    from soni.config import SoniConfig
    from soni.runtime.context import RuntimeContext
    from tests.mocks import MockCommandGenerator, MockSlotExtractor

    mock_context = MagicMock(spec=RuntimeContext)
    mock_context.flow_manager = MagicMock()
    mock_context.du = MockCommandGenerator()
    mock_context.slot_extractor = MockSlotExtractor()
    mock_context.action_handler = AsyncMock()
    mock_context.config = SoniConfig(flows={})

    runtime = Runtime(
        context=mock_context,
        store=None,
        stream_writer=lambda x: None,
        previous=None,
    )
    return runtime
