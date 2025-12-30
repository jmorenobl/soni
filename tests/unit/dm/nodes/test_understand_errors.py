"""Unit tests for NLU error handling in understand_node."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from soni.core.errors import NLUProviderError
from soni.dm.nodes.understand import understand_node
from soni.runtime.context import RuntimeContext


@pytest.fixture
def mock_runtime() -> MagicMock:
    """Create a mock runtime with NLU providers."""
    runtime = MagicMock()
    runtime.context = MagicMock(spec=RuntimeContext)
    # Setup default mocks to avoid unrelated errors
    runtime.context.flow_manager = MagicMock()
    runtime.context.config = MagicMock()
    runtime.context.nlu_provider = AsyncMock()
    runtime.context.slot_extractor = AsyncMock()
    return runtime


def _create_minimal_state(user_message: str = "hello") -> dict:
    """Create a minimal state dict for testing.

    Note: We use dict instead of DialogueState to avoid mypy
    requiring all TypedDict keys in tests.
    """
    return {
        "messages": [],
        "user_message": user_message,
        "flow_stack": [],
        "flow_slots": {},
        "response": None,
        "commands": None,
        "_pending_task": None,
        "_executed_steps": {},
        "_branch_target": None,
        "_flow_changed": None,
        "_loop_flag": None,
        "_pending_responses": [],
    }


@pytest.mark.asyncio
async def test_nlu_pass1_propagates_error(mock_runtime: MagicMock) -> None:
    """Test that NLU pass 1 errors are propagated, not swallowed."""
    # Arrange
    state = _create_minimal_state("hello")

    # Simulate a generic error in NLU provider
    mock_runtime.context.nlu_provider.acall.side_effect = Exception("Generic NLU failure")

    # Act & Assert
    with patch("soni.dm.nodes.understand.DialogueContextBuilder") as MockBuilder:
        mock_builder_instance = MockBuilder.return_value
        mock_builder_instance.build.return_value = {}

        # Should raise NLUProviderError (wrapped from generic Exception)
        with pytest.raises(NLUProviderError, match="NLU Pass 1 failed"):
            await understand_node(state, mock_runtime)  # type: ignore[arg-type]


@pytest.mark.asyncio
async def test_slot_extraction_propagates_error(mock_runtime: MagicMock) -> None:
    """Test that slot extraction errors are propagated."""
    # Arrange
    state = _create_minimal_state("start flow")

    # Mock NLU pass 1 success with a StartFlow command
    mock_cmd = MagicMock()
    mock_cmd.type = "start_flow"
    mock_cmd.flow_name = "test_flow"

    mock_result = MagicMock()
    mock_result.commands = [mock_cmd]
    mock_runtime.context.nlu_provider.acall.return_value = mock_result

    with patch("soni.dm.nodes.understand.DialogueContextBuilder") as MockBuilder:
        mock_builder_instance = MockBuilder.return_value
        # Return some dummy slots so it tries to call extractor
        mock_slot = MagicMock()
        mock_slot.name = "slot1"
        mock_builder_instance.get_slot_definitions.return_value = [mock_slot]
        mock_builder_instance.build.return_value = {}

        # Make slot extractor fail
        mock_runtime.context.slot_extractor.acall.side_effect = NLUProviderError(
            "Slot extraction API down"
        )

        # Act & Assert
        with pytest.raises(NLUProviderError, match="Slot extraction API down"):
            await understand_node(state, mock_runtime)  # type: ignore[arg-type]
