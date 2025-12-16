"""Unit tests for ConfirmNodeFactory."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from soni.compiler.nodes.confirm import ConfirmNodeFactory, _parse_confirmation
from soni.core.config import StepConfig
from soni.core.state import create_empty_dialogue_state


class TestParseConfirmation:
    """Tests for yes/no parsing logic."""

    @pytest.mark.parametrize(
        "message,expected",
        [
            ("yes", True),
            ("YES", True),
            ("Yes", True),
            ("y", True),
            ("Y", True),
            ("si", True),
            ("sí", True),
            ("ok", True),
            ("okay", True),
            ("sure", True),
            ("yep", True),
            ("yeah", True),
            ("confirm", True),
            ("correct", True),
            ("yes please", True),
            ("yes, that's correct", True),
        ],
    )
    def test_parse_yes_responses(self, message: str, expected: bool):
        assert _parse_confirmation(message) is expected

    @pytest.mark.parametrize(
        "message,expected",
        [
            ("no", False),
            ("NO", False),
            ("No", False),
            ("n", False),
            ("N", False),
            ("nope", False),
            ("nah", False),
            ("cancel", False),
            ("deny", False),
            ("wrong", False),
            ("incorrect", False),
            ("no thanks", False),
            ("no, change it", False),
        ],
    )
    def test_parse_no_responses(self, message: str, expected: bool):
        assert _parse_confirmation(message) is expected

    @pytest.mark.parametrize(
        "message",
        [
            "maybe",
            "I'm not sure",
            "what?",
            "",
            "   ",
            "hmm",
            "let me think",
        ],
    )
    def test_parse_unclear_responses(self, message: str):
        assert _parse_confirmation(message) is None


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
    async def test_yes_response_sets_slot_to_true(self, factory, step_config, mock_config):
        """Yes response should set slot to True."""
        node = factory.create(step_config)
        state = create_empty_dialogue_state()
        state["waiting_for_slot"] = "confirmed"
        state["user_message"] = "yes"

        result = await node(state, mock_config)

        assert result["flow_state"] == "active"
        assert result["waiting_for_slot"] is None
        mock_config["configurable"]["runtime_context"].flow_manager.set_slot.assert_called()

    @pytest.mark.asyncio
    async def test_no_response_sets_slot_to_false(self, factory, step_config, mock_config):
        """No response should set slot to False."""
        node = factory.create(step_config)
        state = create_empty_dialogue_state()
        state["waiting_for_slot"] = "confirmed"
        state["user_message"] = "no"

        result = await node(state, mock_config)

        assert result["flow_state"] == "active"
        assert result["waiting_for_slot"] is None

    @pytest.mark.asyncio
    async def test_unclear_response_reasks(self, factory, step_config, mock_config):
        """Unclear response should re-ask and increment retry counter."""
        node = factory.create(step_config)
        state = create_empty_dialogue_state()
        state["waiting_for_slot"] = "confirmed"
        state["user_message"] = "maybe"

        result = await node(state, mock_config)

        assert result["flow_state"] == "waiting_input"
        assert "I didn't understand" in result["last_response"]

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
        state["user_message"] = "unclear response"

        result = await node(state, mock_config)

        assert result["flow_state"] == "active"
        assert "Assuming 'no'" in result["last_response"]
