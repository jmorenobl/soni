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
    """Create a mock RuntimeLoop for testing."""
    from unittest.mock import AsyncMock, MagicMock

    from soni.runtime.loop import RuntimeLoop

    runtime = AsyncMock(spec=RuntimeLoop)
    runtime.process_message.return_value = "Mock response"
    # mock_runtime should also have a context for some tests
    runtime._context = MagicMock()
    runtime._context.du = AsyncMock()
    runtime._context.nlu_provider = runtime._context.du
    runtime._context.slot_extractor = AsyncMock()

    return runtime


@pytest.fixture
def test_client(mock_runtime):
    """FastAPI test client with injected mock runtime."""
    from fastapi.testclient import TestClient

    from soni.server.api import app

    app.state.runtime = mock_runtime
    return TestClient(app)


@pytest.fixture
def mock_llm():
    """Mock LLM for DSPy modules."""
    from unittest.mock import AsyncMock

    llm = AsyncMock()
    llm.return_value = {}
    return llm


@pytest.fixture
def sample_flow_def():
    """Sample flow definition for testing."""
    return {
        "name": "test_flow",
        "description": "Test flow",
        "slots": [{"name": "test_slot", "type": "string"}],
        "steps": [{"type": "say", "message": "Hello"}],
    }
