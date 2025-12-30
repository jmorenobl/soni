"""End-to-end integration tests for Human Input Gate architecture.

Uses mocked NLU and manual node execution to verify deterministic logic.
"""

from typing import Any, cast
from unittest.mock import AsyncMock, MagicMock

import pytest

from soni.core.message_sink import BufferedMessageSink
from soni.core.pending_task import collect, inform, is_collect, is_inform
from soni.core.types import (
    DialogueState,
    FlowDelta,
    _merge_executed_steps,
    _merge_flow_slots,
    add_responses,
)
from soni.dm.nodes.human_input_gate import human_input_gate
from soni.dm.nodes.orchestrator import orchestrator_node
from soni.dm.nodes.understand import understand_node
from soni.flow.manager import FlowManager
from soni.runtime.context import RuntimeContext


class MockRuntime:
    """Mock for LangGraph Runtime."""

    def __init__(self, context: RuntimeContext):
        self.context = context


class MockNLUProvider:
    """Deterministic mock NLU for testing DM logic."""

    def __init__(self):
        self.responses: list[list[dict[str, Any]]] = []
        self._response_index = 0

    def set_responses(self, responses: list[list[dict[str, Any]]]):
        """Set sequence of command responses."""
        self.responses = responses
        self._response_index = 0

    async def acall(
        self, message: str, context: Any, history: list[Any] | None = None
    ) -> MagicMock:
        """Return next predetermined response."""
        if self._response_index < len(self.responses):
            commands = self.responses[self._response_index]
            self._response_index += 1
        else:
            commands = []

        result = MagicMock()
        result.commands = commands
        # Mock model_dump to return the commands if they are dicts
        return result


class MockSubgraphRegistry:
    """Mock subgraph registry returning predetermined results."""

    def __init__(self):
        self.flow_results: dict[str, list[dict]] = {}

    def set_flow_result(self, flow_name: str, outputs: list[dict]):
        """Set outputs for a specific flow."""
        self.flow_results[flow_name] = outputs

    def get(self, flow_name: str) -> MagicMock:
        """Return mock subgraph that yields predetermined outputs."""
        outputs = self.flow_results.get(flow_name, [{}])

        async def mock_astream(state, stream_mode=None):
            # Format depends on stream_mode, but orchestrator uses "updates"
            # which returns {node_name: updates}
            for output in outputs:
                yield {"node": output}

        mock_graph = MagicMock()
        mock_graph.astream = mock_astream
        return mock_graph


@pytest.fixture
def mock_context():
    """Create fully mocked RuntimeContext."""
    config = MagicMock()
    config.flows = {
        "check_balance": MagicMock(description="Check balance"),
        "transfer_funds": MagicMock(description="Transfer funds"),
    }
    config.settings.rephrase_responses = False

    return RuntimeContext(
        flow_manager=FlowManager(),
        subgraph_registry=MockSubgraphRegistry(),
        message_sink=BufferedMessageSink(),
        nlu_provider=cast(Any, MockNLUProvider()),
        slot_extractor=AsyncMock(),
        action_registry=MagicMock(),
        config=config,
        rephraser=None,
        command_handlers=None,
    )


def apply_updates(state: DialogueState, updates: dict[str, Any], node_name: str = "") -> None:
    """Apply node updates to state using manual reducers."""
    if not updates:
        return
    # print(f"DEBUG [{node_name}]: Applying updates {list(updates.keys())}")
    for key, value in updates.items():
        if key == "messages":
            from langgraph.graph.message import add_messages

            state["messages"] = add_messages(state.get("messages", []), value)
        elif key == "flow_slots":
            current: dict[str, dict[str, Any]] = state.get("flow_slots") or {}
            state["flow_slots"] = _merge_flow_slots(current, value)
        elif key == "_executed_steps":
            current_steps: dict[str, set[str]] = state.get("_executed_steps") or {}
            state["_executed_steps"] = _merge_executed_steps(current_steps, value)
        elif key == "_pending_responses":
            state["_pending_responses"] = add_responses(state.get("_pending_responses", []), value)
        else:
            # Most other fields use _last_value_str or _last_value_any which now both return 'new'
            # We use Unpack/cast or just direct assignment with ignore for the dynamic key on TypedDict
            # Mypy doesn't like dynamic keys on TypedDict.
            # safe way: use a cast or ignore
            state[key] = value  # type: ignore[literal-required]


class TestHumanInputGateE2E:
    """End-to-end tests for the Human Input Gate architecture using manual execution."""

    @pytest.mark.asyncio
    async def test_start_flow_triggers_collect(self, mock_context):
        """Test: User starts flow → NLU returns StartFlow → Orchestrator invokes subgraph → CollectTask returned."""
        # Arrange
        mock_runtime = MockRuntime(mock_context)
        from soni.core.state import create_empty_state

        state = create_empty_state()
        state["user_message"] = "Check my balance"

        # Mock NLU
        mock_context.nlu_provider.set_responses(
            [[{"type": "start_flow", "flow_name": "check_balance"}]]
        )

        # Mock subgraph
        mock_context.subgraph_registry.set_flow_result(
            "check_balance", [{"_pending_task": collect(prompt="Which account?", slot="account")}]
        )

        # Act - Manual cycle execution
        # 1. Human Input Gate
        updates = await human_input_gate(state)
        apply_updates(state, updates, "human_input_gate")

        # 2. Understand node (NLU)
        updates = await understand_node(state, mock_runtime)
        apply_updates(state, updates, "understand_node")

        # 3. Orchestrator node
        updates = await orchestrator_node(state, mock_runtime)
        apply_updates(state, updates, "orchestrator_node")

        # Assert
        assert "_pending_task" in state and state["_pending_task"] is not None
        assert is_collect(state["_pending_task"])
        assert state["_pending_task"]["prompt"] == "Which account?"

    @pytest.mark.asyncio
    async def test_inform_without_wait_sends_immediately(self, mock_context):
        """Test: InformTask without wait_for_ack sends message and continues."""
        # Arrange
        mock_runtime = MockRuntime(mock_context)
        sink = cast(BufferedMessageSink, mock_context.message_sink)
        from soni.core.state import create_empty_state

        state = create_empty_state()
        state["user_message"] = "Check balance"

        mock_context.nlu_provider.set_responses(
            [[{"type": "start_flow", "flow_name": "check_balance"}]]
        )

        mock_context.subgraph_registry.set_flow_result(
            "check_balance",
            [{"_pending_task": inform(prompt="Your balance is $1,234", wait_for_ack=False)}],
        )

        # Act
        # 1. Human Input Gate
        updates = await human_input_gate(state)
        apply_updates(state, updates, "human_input_gate")

        # 2. Understand node
        updates = await understand_node(state, mock_runtime)
        apply_updates(state, updates, "understand_node")

        # 3. Orchestrator node
        updates = await orchestrator_node(state, mock_runtime)
        apply_updates(state, updates, "orchestrator_node")

        # Assert
        assert len(sink.messages) > 0
        assert sink.messages[0] == "Your balance is $1,234"

    @pytest.mark.asyncio
    async def test_cancel_flow_pops_stack(self, mock_context):
        """Test: CancelFlow command pops flow from stack."""
        # Arrange
        mock_runtime = MockRuntime(mock_context)
        from soni.core.state import create_empty_state

        state = create_empty_state()

        # Initial state with active flow
        _, delta = mock_context.flow_manager.push_flow(state, "transfer_funds")
        apply_updates(state, delta.to_dict(), "setup")

        mock_context.nlu_provider.set_responses([[{"type": "cancel_flow"}]])

        # Act
        state["user_message"] = "Cancel"

        # 1. Human Input Gate
        updates = await human_input_gate(state)
        apply_updates(state, updates, "human_input_gate")

        # 2. Understand node - Returns commands (no longer processes them)
        updates = await understand_node(state, mock_runtime)
        apply_updates(state, updates, "understand_node")

        # 3. Orchestrator node - Processes commands including cancel_flow
        updates = await orchestrator_node(state, mock_runtime)
        apply_updates(state, updates, "orchestrator_node")

        # ASSERT: Stack should be empty AFTER orchestrator_node (Issue #3 consolidation)
        assert state.get("flow_stack") == []

    @pytest.mark.asyncio
    async def test_no_obsolete_fields_in_state(self, mock_context):
        """Test: Result does not contain obsolete fields."""
        # Arrange
        mock_runtime = MockRuntime(mock_context)
        from soni.core.state import create_empty_state

        state = create_empty_state()
        state["user_message"] = "Hello"
        mock_context.nlu_provider.set_responses([[]])

        # Act
        updates = await human_input_gate(state)
        apply_updates(state, updates, "human_input_gate")
        updates = await understand_node(state, mock_runtime)
        apply_updates(state, updates, "understand_node")
        updates = await orchestrator_node(state, mock_runtime)
        apply_updates(state, updates, "orchestrator_node")

        # Assert
        assert "_need_input" not in state
        assert "_pending_prompt" not in state
