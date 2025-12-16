"""Unit tests for ConfirmNodeFactory."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from soni.compiler.nodes.confirm import ConfirmNodeFactory, _find_confirmation_command
from soni.core.config import StepConfig
from soni.core.state import create_empty_dialogue_state


class TestFindConfirmationCommand:
    """Tests for NLU command parsing."""

    def test_find_affirm_command_dict(self):
        """Should find affirm command from dict."""
        commands = [{"type": "affirm"}]
        is_affirmed, slot = _find_confirmation_command(commands)
        assert is_affirmed is True
        assert slot is None

    def test_find_deny_command_dict(self):
        """Should find deny command from dict."""
        commands = [{"type": "deny"}]
        is_affirmed, slot = _find_confirmation_command(commands)
        assert is_affirmed is False
        assert slot is None

    def test_find_deny_with_slot_to_change(self):
        """Should extract slot_to_change from deny command."""
        commands = [{"type": "deny", "slot_to_change": "destination"}]
        is_affirmed, slot = _find_confirmation_command(commands)
        assert is_affirmed is False
        assert slot == "destination"

    def test_no_confirmation_command(self):
        """Should return None when no affirm/deny found."""
        commands = [{"type": "set_slot", "slot": "foo"}]
        is_affirmed, slot = _find_confirmation_command(commands)
        assert is_affirmed is None
        assert slot is None

    def test_empty_commands_list(self):
        """Should return None for empty list."""
        is_affirmed, slot = _find_confirmation_command([])
        assert is_affirmed is None
        assert slot is None

    def test_find_command_with_command_type_key(self):
        """Should work with command_type key (alternative format)."""
        commands = [{"command_type": "affirm"}]
        is_affirmed, slot = _find_confirmation_command(commands)
        assert is_affirmed is True

    def test_find_command_from_object(self):
        """Should work with command objects."""
        cmd = MagicMock()
        cmd.type = "deny"
        cmd.slot_to_change = "origin"
        is_affirmed, slot = _find_confirmation_command([cmd])
        assert is_affirmed is False
        assert slot == "origin"


class TestConfirmNodeFactory:
    """Tests for ConfirmNodeFactory."""

    @pytest.fixture
    def factory(self):
        return ConfirmNodeFactory()

    @pytest.fixture
    def step_config(self):
        return StepConfig(
            step="confirm_booking",
            type="confirm",
            slot="confirmed",
            message="Do you want to confirm this booking?",
            max_retries=3,
        )

    @pytest.fixture
    def mock_config(self):
        mock_fm = MagicMock()
        mock_fm.get_slot = MagicMock(return_value=None)
        mock_fm.set_slot = AsyncMock()
        return {
            "configurable": {
                "runtime_context": MagicMock(flow_manager=mock_fm),
            }
        }

    @pytest.mark.asyncio
    async def test_first_visit_asks_for_confirmation(self, factory, step_config, mock_config):
        """First visit should prompt for confirmation."""
        node = factory.create(step_config)
        state = create_empty_dialogue_state()

        result = await node(state, mock_config)

        assert result["flow_state"] == "waiting_input"
        assert result["waiting_for_slot"] == "confirmed"
        assert "Do you want to confirm this booking?" in result["last_response"]

    @pytest.mark.asyncio
    async def test_affirm_command_sets_slot_to_true(self, factory, step_config, mock_config):
        """Affirm command from NLU should set slot to True."""
        node = factory.create(step_config)
        state = create_empty_dialogue_state()
        state["waiting_for_slot"] = "confirmed"
        state["commands"] = [{"type": "affirm"}]

        result = await node(state, mock_config)

        assert result["flow_state"] == "active"
        assert result["waiting_for_slot"] is None
        mock_config["configurable"]["runtime_context"].flow_manager.set_slot.assert_called()

    @pytest.mark.asyncio
    async def test_deny_command_sets_slot_to_false(self, factory, step_config, mock_config):
        """Deny command from NLU should set slot to False."""
        node = factory.create(step_config)
        state = create_empty_dialogue_state()
        state["waiting_for_slot"] = "confirmed"
        state["commands"] = [{"type": "deny"}]

        result = await node(state, mock_config)

        assert result["flow_state"] == "active"
        assert result["waiting_for_slot"] is None

    @pytest.mark.asyncio
    async def test_no_command_reasks(self, factory, step_config, mock_config):
        """No affirm/deny command should re-ask."""
        node = factory.create(step_config)
        state = create_empty_dialogue_state()
        state["waiting_for_slot"] = "confirmed"
        state["commands"] = []  # No confirmation command

        result = await node(state, mock_config)

        assert result["flow_state"] == "waiting_input"
        assert "yes or no" in result["last_response"]

    @pytest.mark.asyncio
    async def test_already_filled_slot_skips_confirmation(self, factory, step_config, mock_config):
        """If slot already has a value, skip confirmation."""
        mock_config["configurable"]["runtime_context"].flow_manager.get_slot.return_value = True
        node = factory.create(step_config)
        state = create_empty_dialogue_state()

        result = await node(state, mock_config)

        assert result["flow_state"] == "active"

    def test_missing_slot_raises_error(self, factory):
        """Missing slot field should raise ValueError."""
        step = StepConfig(step="bad_confirm", type="confirm")

        with pytest.raises(ValueError, match="missing required field 'slot'"):
            factory.create(step)


class TestConfirmNodeMaxRetries:
    """Tests for max_retries behavior."""

    @pytest.fixture
    def factory(self):
        return ConfirmNodeFactory()

    @pytest.fixture
    def step_config(self):
        return StepConfig(
            step="confirm_booking",
            type="confirm",
            slot="confirmed",
            max_retries=2,
        )

    @pytest.mark.asyncio
    async def test_max_retries_exceeded_sets_false(self, factory, step_config):
        """Exceeding max retries should set slot to False."""
        mock_fm = MagicMock()
        # Simulate already at max retries
        mock_fm.get_slot.side_effect = lambda state, key: (
            None if key == "confirmed" else 2  # retry counter at max
        )
        mock_fm.set_slot = AsyncMock()

        mock_config = {
            "configurable": {
                "runtime_context": MagicMock(flow_manager=mock_fm),
            }
        }

        node = factory.create(step_config)
        state = create_empty_dialogue_state()
        state["waiting_for_slot"] = "confirmed"
        state["commands"] = []  # No confirmation command

        result = await node(state, mock_config)

        assert result["flow_state"] == "active"
        assert "Assuming 'no'" in result["last_response"]

    @pytest.mark.asyncio
    async def test_deny_with_slot_to_change_waits_for_slot(self, factory, step_config):
        """Deny with slot_to_change should wait for that slot's new value."""
        mock_fm = MagicMock()
        mock_fm.get_slot.return_value = None
        mock_fm.set_slot = AsyncMock()

        mock_config = {
            "configurable": {
                "runtime_context": MagicMock(flow_manager=mock_fm),
            }
        }

        node = factory.create(step_config)
        state = create_empty_dialogue_state()
        state["waiting_for_slot"] = "confirmed"
        state["commands"] = [{"type": "deny", "slot_to_change": "destination"}]
        state["flow_slots"] = {}

        result = await node(state, mock_config)

        # New behavior: waits for the slot to be modified
        assert result["flow_state"] == "waiting_input"
        assert result["waiting_for_slot"] == "destination"
        assert "change" in result["last_response"].lower()
