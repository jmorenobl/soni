import logging
from unittest.mock import AsyncMock, MagicMock

import pytest

from soni.core.commands import CancelFlow
from soni.core.types import DialogueState, RuntimeContext
from soni.dm.nodes.understand import understand_node


@pytest.mark.asyncio
async def test_log_unhandled_cancel_flow(caplog):
    """Test that CancelFlow command triggers a warning log in understand_node."""
    # Arrange
    caplog.set_level(logging.WARNING)

    from soni.core.constants import FlowState
    from soni.core.state import create_empty_dialogue_state

    state = create_empty_dialogue_state()
    state.update(
        {
            "user_message": "cancel",
            "flow_state": FlowState.ACTIVE,
        }
    )

    # Mock NLU output with CancelFlow
    mock_du = MagicMock()
    mock_du.aforward = AsyncMock(return_value=MagicMock(commands=[CancelFlow(type="cancel_flow")]))

    mock_fm = MagicMock()
    mock_fm.get_active_context.return_value = None

    context = RuntimeContext(
        config=MagicMock(), flow_manager=mock_fm, du=mock_du, action_handler=MagicMock()
    )

    from langchain_core.runnables import RunnableConfig

    # Use real dict for config since get_runtime_context uses item access
    config: RunnableConfig = {"configurable": {"runtime_context": context}}

    # Act
    await understand_node(state, config)

    # Assert
    assert "Unhandled command type" in caplog.text
    assert "cancel_flow" in caplog.text
