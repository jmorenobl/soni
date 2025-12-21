from unittest.mock import AsyncMock, MagicMock

import pytest
from langgraph.runtime import Runtime
from langgraph.types import Command

from soni.core.state import create_empty_dialogue_state
from soni.core.types import DialogueState, RuntimeContext


class TestRuntimeInjection:
    """Tests for LangGraph Runtime pattern."""

    @pytest.fixture
    def mock_runtime(self) -> Runtime[RuntimeContext]:
        """Create mock Runtime with RuntimeContext."""
        from soni.config import SoniConfig

        mock_context = MagicMock(spec=RuntimeContext)
        mock_context.flow_manager = MagicMock()
        mock_context.du = AsyncMock()
        mock_context.action_handler = AsyncMock()
        # Use real minimal config to pass Pydantic validation
        mock_context.config = SoniConfig(flows={}, slots={})
        mock_context.slot_extractor = None

        return Runtime(
            context=mock_context,
            store=None,
            stream_writer=lambda x: None,
            previous=None,
        )

    @pytest.mark.asyncio
    async def test_understand_node_accepts_runtime(self, mock_runtime: Runtime[RuntimeContext]):
        """Test that understand_node accepts Runtime[RuntimeContext]."""
        from soni.dm.nodes.understand import understand_node

        state: DialogueState = create_empty_dialogue_state()
        state["user_message"] = "hello"

        # Configure mock DU
        mock_runtime.context.du.acall = AsyncMock(return_value=MagicMock(commands=[]))
        mock_runtime.context.flow_manager.get_active_context.return_value = None

        # Should not raise TypeError
        result = await understand_node(state, mock_runtime)
        assert isinstance(result, dict)

    @pytest.mark.asyncio
    async def test_execute_node_accepts_runtime(self, mock_runtime: Runtime[RuntimeContext]):
        """Test that execute_node accepts Runtime[RuntimeContext]."""
        from soni.dm.nodes.execute import execute_node

        state: DialogueState = create_empty_dialogue_state()

        # Should not raise TypeError
        result = await execute_node(state, mock_runtime)
        assert isinstance(result, (dict, Command))


class TestActionNodeFactory:
    """Tests for action node factory with Runtime."""

    @pytest.mark.asyncio
    async def test_action_node_uses_runtime(self):
        """Test that action nodes accept Runtime parameter."""
        from soni.compiler.nodes.action import ActionNodeFactory
        from soni.config.steps import ActionStepConfig

        step = ActionStepConfig(
            step="test",
            call="test_action",
            slot="result",
        )

        factory = ActionNodeFactory()
        node_fn = factory.create(step)

        mock_context = MagicMock(spec=RuntimeContext)
        mock_context.action_handler = AsyncMock()
        mock_context.action_handler.execute = AsyncMock(return_value={"data": "ok"})
        mock_context.flow_manager = MagicMock()
        mock_context.flow_manager.get_active_context.return_value = {
            "flow_id": "test_123",
            "flow_name": "test",
        }
        mock_context.flow_manager.get_all_slots.return_value = {}

        mock_runtime = Runtime(
            context=mock_context,
            store=None,
            stream_writer=lambda x: None,
            previous=None,
        )

        state: DialogueState = create_empty_dialogue_state()
        state["flow_stack"] = [{"flow_id": "test_123"}]  # type: ignore

        # Should execute without TypeError
        result = await node_fn(state, mock_runtime)
        assert isinstance(result, dict)
