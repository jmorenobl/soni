"""Shared fixtures for Soni tests.

Uses MockSoniDU for deterministic, fast tests without LLM API calls.
"""

import pytest


class MockNLUOutput:
    """Mock NLU output for deterministic tests."""
    
    def __init__(self, commands: list):
        self.commands = commands
        self.confidence = 1.0


class MockCommand:
    """Mock command for tests."""
    
    def __init__(self, cmd_dict: dict):
        self._data = cmd_dict
        self.type = cmd_dict.get("type")
        self.flow_name = cmd_dict.get("flow_name")
        self.slot = cmd_dict.get("slot")
        self.value = cmd_dict.get("value")
        self.message = cmd_dict.get("message")
    
    def model_dump(self) -> dict:
        return self._data


class MockSoniDU:
    """Deterministic mock for SoniDU.
    
    Returns StartFlow for first flow in config if message not empty.
    This simulates NLU detecting intent based on available flows.
    """
    
    def __init__(self, default_flow: str | None = None):
        self.default_flow = default_flow
        self._call_count = 0
    
    @classmethod
    def create_with_best_model(cls) -> "MockSoniDU":
        return cls()
    
    async def acall(self, message: str, context) -> MockNLUOutput:
        """Return deterministic StartFlow command."""
        self._call_count += 1
        
        if not message:
            return MockNLUOutput(commands=[])
        
        # Get first available flow from context
        if hasattr(context, "available_flows") and context.available_flows:
            flow_name = context.available_flows[0].name
            return MockNLUOutput(commands=[
                MockCommand({"type": "start_flow", "flow_name": flow_name})
            ])
        
        # Fallback: return chitchat
        return MockNLUOutput(commands=[
            MockCommand({"type": "chitchat", "message": "I'm here to help!"})
        ])


# Patch SoniDU module-level to use MockSoniDU
import soni.du.modules
soni.du.modules.SoniDU = MockSoniDU  # type: ignore[attr-defined]


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

    mock_context = MagicMock(spec=RuntimeContext)
    mock_context.flow_manager = MagicMock()
    mock_context.du = MockSoniDU()
    mock_context.action_handler = AsyncMock()
    # Use real minimal config to pass Pydantic validation
    mock_context.config = SoniConfig(flows={})
    mock_context.slot_extractor = None

    runtime = Runtime(
        context=mock_context,
        store=None,
        stream_writer=lambda x: None,
        previous=None,
    )
    return runtime

