"""Unit tests for validate_slot helper functions."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from soni.core.state import create_empty_state
from soni.core.types import DialogueState, FlowContext
from soni.dm.nodes.validate_slot import (
    _detect_correction_or_modification,
    _handle_correction_flow,
    _process_all_slots,
)


@pytest.fixture
def mock_active_ctx():
    """Create a mock active flow context."""
    return {
        "flow_id": "book_flight_123",
        "flow_name": "book_flight",
        "flow_state": "active",
        "current_step": "collect_origin",
        "outputs": {},
        "started_at": 0.0,
        "paused_at": None,
        "completed_at": None,
        "context": None,
    }


@pytest.fixture
def mock_normalizer():
    """Create a mock normalizer."""
    normalizer = AsyncMock()
    normalizer.normalize_slot.return_value = "normalized_value"
    return normalizer


class TestProcessAllSlots:
    """Test slot processing helper."""

    @pytest.mark.asyncio
    async def test_process_dict_slots(self, mock_active_ctx, mock_normalizer):
        """Test processing slots in dict format."""
        # Arrange
        state = create_empty_state()
        state["flow_slots"] = {}
        slots = [
            {"name": "origin", "value": "New York"},
            {"name": "destination", "value": "Los Angeles"},
        ]

        # Act
        flow_slots = await _process_all_slots(slots, state, mock_active_ctx, mock_normalizer)

        # Assert
        assert flow_slots["book_flight_123"]["origin"] == "normalized_value"
        assert flow_slots["book_flight_123"]["destination"] == "normalized_value"
        assert mock_normalizer.normalize_slot.call_count == 2

    @pytest.mark.asyncio
    async def test_process_slotvalue_slots(self, mock_active_ctx, mock_normalizer):
        """Test processing SlotValue model slots."""
        # Arrange
        from soni.du.models import SlotValue

        state = create_empty_state()
        state["flow_slots"] = {}
        slots = [
            SlotValue(name="origin", value="New York", confidence=0.9, action="provide"),
            SlotValue(name="destination", value="Los Angeles", confidence=0.9, action="provide"),
        ]

        # Act
        flow_slots = await _process_all_slots(slots, state, mock_active_ctx, mock_normalizer)

        # Assert
        assert flow_slots["book_flight_123"]["origin"] == "normalized_value"
        assert flow_slots["book_flight_123"]["destination"] == "normalized_value"

    @pytest.mark.asyncio
    async def test_process_string_slots(self, mock_active_ctx, mock_normalizer):
        """Test processing string slots."""
        # Arrange
        state = create_empty_state()
        state["flow_slots"] = {}
        state["waiting_for_slot"] = "origin"
        slots = ["New York"]

        # Act
        flow_slots = await _process_all_slots(slots, state, mock_active_ctx, mock_normalizer)

        # Assert
        assert flow_slots["book_flight_123"]["origin"] == "normalized_value"

    @pytest.mark.asyncio
    async def test_process_unknown_format(self, mock_active_ctx, mock_normalizer):
        """Test processing unknown slot format (should skip)."""
        # Arrange
        state = create_empty_state()
        state["flow_slots"] = {}
        slots = [123]  # Invalid format

        # Act
        flow_slots = await _process_all_slots(slots, state, mock_active_ctx, mock_normalizer)

        # Assert: Should skip invalid format, no slots processed
        assert flow_slots["book_flight_123"] == {}
        assert mock_normalizer.normalize_slot.call_count == 0


class TestDetectCorrectionOrModification:
    """Test correction detection helper."""

    def test_detect_correction_by_message_type(self):
        """Test detection via message_type."""
        # Arrange
        slots = [{"name": "origin", "value": "Denver", "action": "provide"}]
        message_type = "correction"

        # Act
        result = _detect_correction_or_modification(slots, message_type)

        # Assert
        assert result is True

    def test_detect_correction_by_slot_action(self):
        """Test detection via slot action."""
        # Arrange
        slots = [{"name": "origin", "value": "Denver", "action": "correct"}]
        message_type = "slot_value"

        # Act
        result = _detect_correction_or_modification(slots, message_type)

        # Assert
        assert result is True

    def test_fallback_slot_not_correction(self):
        """Test that fallback slots are not treated as corrections."""
        # Arrange: Fallback slot has action=provide and confidence=0.5
        slots = [{"name": "origin", "value": "Denver", "action": "provide", "confidence": 0.5}]
        message_type = "slot_value"

        # Act
        result = _detect_correction_or_modification(slots, message_type)

        # Assert
        assert result is False

    def test_normal_slot_not_correction(self):
        """Test that normal slots are not treated as corrections."""
        # Arrange
        slots = [{"name": "origin", "value": "New York", "action": "provide", "confidence": 0.9}]
        message_type = "slot_value"

        # Act
        result = _detect_correction_or_modification(slots, message_type)

        # Assert
        assert result is False


class TestHandleCorrectionFlow:
    """Test correction flow handling helper."""

    def test_handle_correction_returns_to_previous_step(self):
        """Test that correction returns to previous step."""
        # Arrange
        state = create_empty_state()
        state["flow_stack"] = [
            {
                "flow_id": "book_flight_123",
                "flow_name": "book_flight",
                "flow_state": "active",
                "current_step": "collect_destination",
                "outputs": {},
                "started_at": 0.0,
                "paused_at": None,
                "completed_at": None,
                "context": None,
            }
        ]
        state["flow_slots"] = {"book_flight_123": {"origin": "Denver"}}
        state["conversation_state"] = "waiting_for_slot"

        flow_slots = {"book_flight_123": {"origin": "Denver"}}
        previous_step = "collect_origin"

        # Mock step_manager
        mock_step_manager = MagicMock()
        mock_step_config = MagicMock()
        mock_step_config.type = "collect"
        mock_step_manager.get_current_step_config.return_value = mock_step_config
        mock_step_manager.config.flows = {
            "book_flight": MagicMock(
                steps=[
                    MagicMock(step="collect_origin", type="collect", slot="origin"),
                    MagicMock(step="collect_destination", type="collect", slot="destination"),
                ]
            )
        }

        mock_flow_manager = MagicMock()
        mock_flow_manager.get_active_context.return_value = {
            "flow_id": "book_flight_123",
            "flow_name": "book_flight",
            "current_step": "collect_destination",
        }

        mock_runtime = MagicMock()
        mock_runtime.context = {
            "step_manager": mock_step_manager,
            "flow_manager": mock_flow_manager,
        }

        # Act
        result = _handle_correction_flow(state, mock_runtime, flow_slots, previous_step)

        # Assert
        assert result["conversation_state"] == "waiting_for_slot"
        assert result["current_step"] == "collect_origin"
        assert "flow_slots" in result
