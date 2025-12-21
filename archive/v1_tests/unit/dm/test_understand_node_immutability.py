"""Tests to verify understand_node does not mutate input state."""

from unittest.mock import AsyncMock, Mock

import pytest

# We need to import the node function. It might not be exposed directly if it's inside a module
# but usually it's in soni.dm.nodes.understand or similar.
# Assuming we can test the logic that *would* be inside understand_node,
# or create_state_view helper directly once it exists.
# For TDD, we test the behavior.
from soni.core.constants import FlowContextState
from soni.core.state import create_empty_dialogue_state
from soni.core.types import DialogueState
from soni.dm.nodes.understand import create_state_view, understand_node


class TestCreateStateView:
    """Tests for the create_state_view helper function.

    These tests will fail initially because create_state_view is not yet implemented/exposed.
    """

    def test_state_view_includes_base_state(self):
        """Test that state_view contains all base state fields."""
        base = create_empty_dialogue_state()
        base["user_message"] = "hello"

        view = create_state_view(base, {})

        assert view["user_message"] == "hello"

    def test_state_view_overlays_updates(self):
        """Test that accumulated updates are applied to view."""
        base = create_empty_dialogue_state()
        base["flow_stack"] = [{"flow_id": "old"}]

        updates = {"flow_stack": [{"flow_id": "new"}]}
        view = create_state_view(base, updates)

        assert view["flow_stack"] == [{"flow_id": "new"}]
        assert base["flow_stack"] == [{"flow_id": "old"}]  # Original unchanged

    def test_state_view_does_not_modify_base(self):
        """Test that creating a view does not modify base state."""
        base = create_empty_dialogue_state()
        original_id = id(base["flow_stack"])

        _ = create_state_view(base, {"flow_stack": []})

        assert id(base["flow_stack"]) == original_id


class TestUnderstandNodeImmutability:
    """Tests to verify understand_node does not mutate input state."""

    @pytest.fixture
    def base_state(self) -> DialogueState:
        """Create a base state for testing."""
        state = create_empty_dialogue_state()
        state["flow_stack"] = [
            {
                "flow_id": "original",
                "flow_name": "test",
                "flow_state": FlowContextState.ACTIVE,
                "current_step": None,
                "step_index": 0,
                "outputs": {},
                "started_at": 0,
            }
        ]
        state["flow_slots"] = {"original": {"slot1": "value1"}}
        return state

    @pytest.fixture
    def mock_runtime_context(self):
        mock_flow_manager = Mock()
        mock_flow_manager.get_active_flow_id.return_value = "original"
        # Return a valid context dict instead of Mock
        mock_flow_manager.get_active_context.return_value = {
            "flow_id": "original",
            "flow_name": "test",
        }

        mock_du = Mock()

        mock_config = Mock()
        mock_config.flows = {}
        mock_config.slots = {}

        # Need to import RuntimeContext
        from soni.core.types import RuntimeContext

        ctx = RuntimeContext(
            config=mock_config,
            flow_manager=mock_flow_manager,
            du=mock_du,
            action_handler=Mock(),
            slot_extractor=Mock(),
        )

        # Use a simple Mock instead of Runtime class to avoid TypeError in tests
        # The error "obj (instance of Runtime) is not an instance of type" implies
        # class mismatch or super() issues in testing context.
        # Since we only read .context, a Mock is sufficient and safer here.
        mock_runtime = Mock()
        mock_runtime.context = ctx
        return mock_runtime

    @pytest.mark.asyncio
    async def test_understand_node_does_not_mutate_flow_stack(
        self, base_state: DialogueState, mock_runtime_context
    ):
        """Test that understand_node does not mutate the input flow_stack."""
        # Arrange
        original_stack = list(base_state["flow_stack"])  # Copy for comparison

        # Mock DU to return a command that would normally modify stack (e.g., StartFlow)
        # However, understand_node logic is complex and relies on CommandRegistry.
        # We need to mock the registry or the DU + registry interaction.

        # Strategy: We will patch the part of understand_node that iterates commands
        # OR we can rely on the fact that if we mocked everything, it shouldn't touch state.
        # BUT the bug is specifically about DIRECT mutation.

        # Let's mock the CommandRegistry dispatch to return an update
        from soni.dm.nodes.command_registry import CommandHandlerRegistry, CommandResult

        mock_registry = Mock(spec=CommandHandlerRegistry)
        # Return a result that has updates
        mock_registry.dispatch = AsyncMock(
            return_value=CommandResult(updates={"flow_stack": [{"flow_id": "NEW"}]})
        )

        # We need to inject this mock registry into the node.
        # understand_node instantiates CommandRegistry internally or gets it from context?
        # Looking at previous context, it seems it might instantiate it.
        # If so, we might need to patch 'soni.dm.nodes.understand.CommandRegistry'.

        # Assuming it's patched:
        from unittest.mock import patch

        from soni.core.commands import ChitChat
        from soni.du.models import NLUOutput

        # Use valid command to avoid iteration errors if logic expects objects
        nlu_output = NLUOutput(commands=[ChitChat(message="hi")])

        with patch("soni.dm.nodes.understand.get_command_registry", return_value=mock_registry):
            # Also mock get_flow_slot_definitions used in understand_node
            with patch("soni.du.service.get_flow_slot_definitions", return_value=[]):
                # Mock SlotExtractor
                mock_runtime_context.custom_components = {}
                mock_runtime_context.context.du.acall = AsyncMock(return_value=nlu_output)

                # Act
                await understand_node(base_state, mock_runtime_context)

        # Assert - Original state should be unchanged
        # The mutation happened at: state["flow_stack"] = result.updates["flow_stack"]
        assert base_state["flow_stack"] == original_stack, (
            "understand_node mutated flow_stack directly!"
        )

    @pytest.mark.asyncio
    async def test_understand_node_does_not_mutate_flow_slots(
        self, base_state: DialogueState, mock_runtime_context
    ):
        """Test that understand_node does not mutate the input flow_slots."""
        # Arrange
        original_slots = dict(base_state["flow_slots"])  # Copy for comparison

        from soni.dm.nodes.command_registry import CommandHandlerRegistry, CommandResult

        mock_registry = Mock(spec=CommandHandlerRegistry)
        mock_registry.dispatch = AsyncMock(
            return_value=CommandResult(updates={"flow_slots": {"original": {"new": "val"}}})
        )

        from soni.core.commands import ChitChat
        from soni.du.models import NLUOutput

        nlu_output = NLUOutput(commands=[ChitChat(message="hi")])

        from unittest.mock import patch

        with patch("soni.dm.nodes.understand.get_command_registry", return_value=mock_registry):
            with patch("soni.du.service.get_flow_slot_definitions", return_value=[]):
                mock_runtime_context.context.du.acall = AsyncMock(return_value=nlu_output)
                await understand_node(base_state, mock_runtime_context)

        # Assert - Original state should be unchanged
        assert base_state["flow_slots"] == original_slots, (
            "understand_node mutated flow_slots directly!"
        )

    @pytest.mark.asyncio
    async def test_subsequent_handlers_see_accumulated_updates(
        self, base_state: DialogueState, mock_runtime_context
    ):
        """Test that handlers in sequence can see previous updates via state_view."""
        # Arrange
        from soni.core.commands import ChitChat
        from soni.dm.nodes.command_registry import CommandHandlerRegistry, CommandResult
        from soni.du.models import NLUOutput

        # Two commands
        nlu_output = NLUOutput(commands=[ChitChat(message="step1"), ChitChat(message="step2")])

        mock_registry = Mock(spec=CommandHandlerRegistry)

        # We need check what state was passed to second dispatch
        captured_states = []

        async def mock_dispatch(cmd, state, ctx, expected_slot):
            captured_states.append(state)
            if cmd.message == "step1":
                return CommandResult(updates={"flow_stack": [{"flow_id": "NEW"}]})
            return CommandResult(updates={})

        mock_registry.dispatch = AsyncMock(side_effect=mock_dispatch)

        from unittest.mock import patch

        with patch("soni.dm.nodes.understand.get_command_registry", return_value=mock_registry):
            with patch("soni.du.service.get_flow_slot_definitions", return_value=[]):
                mock_runtime_context.context.du.acall = AsyncMock(return_value=nlu_output)
                await understand_node(base_state, mock_runtime_context)

        # Assert
        assert len(captured_states) == 2
        # First call sees original state
        assert captured_states[0]["flow_stack"] == base_state["flow_stack"]
        # Second call sees UPDATED state (via view)
        assert captured_states[1]["flow_stack"] == [{"flow_id": "NEW"}]
        # But BASE STATE remains immutable
        assert base_state["flow_stack"] != [{"flow_id": "NEW"}]
