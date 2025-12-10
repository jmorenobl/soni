"""Unit tests for handle_correction node.

All tests use mocked NLU for determinism.

Design Reference: docs/design/10-dsl-specification/06-patterns.md:49-80
Pattern: "Correction: User fixes previous value → Update slot, return to step"
"""

from unittest.mock import AsyncMock, MagicMock

import pytest

from soni.dm.nodes.handle_correction import _get_response_template, handle_correction_node
from soni.du.models import MessageType, SlotValue

# === TESTS FOR SLOT FORMATS ===


@pytest.mark.asyncio
async def test_handle_correction_slotvalue_format(
    create_state_with_slots, mock_nlu_correction, mock_runtime
):
    """Test that handle_correction handles SlotValue object format."""
    # Arrange
    state = create_state_with_slots(
        "book_flight", slots={"destination": "Madrid"}, current_step="collect_date"
    )
    # Mock NLU with SlotValue format
    nlu_result = mock_nlu_correction.predict.return_value
    state["nlu_result"] = nlu_result.model_dump()

    mock_runtime.context["normalizer"].normalize_slot.return_value = "Barcelona"

    # Act
    result = await handle_correction_node(state, mock_runtime)

    # Assert
    assert result["flow_slots"]["flow_1"]["destination"] == "Barcelona"
    assert result["metadata"]["_correction_slot"] == "destination"


@pytest.mark.asyncio
async def test_handle_correction_dict_format(create_state_with_slots, mock_runtime):
    """Test that handle_correction handles dict format."""
    # Arrange
    state = create_state_with_slots("book_flight", slots={"destination": "Madrid"})
    # Mock NLU result as dict
    state["nlu_result"] = {
        "message_type": "correction",
        "command": "continue",
        "slots": [{"name": "destination", "value": "Barcelona"}],
        "confidence": 0.95,
    }

    mock_runtime.context["normalizer"].normalize_slot.return_value = "Barcelona"

    # Act
    result = await handle_correction_node(state, mock_runtime)

    # Assert
    assert result["flow_slots"]["flow_1"]["destination"] == "Barcelona"


@pytest.mark.asyncio
async def test_handle_correction_unknown_format(create_state_with_slots, mock_runtime):
    """Test that handle_correction handles unknown format."""
    # Arrange
    state = create_state_with_slots("book_flight", slots={"origin": "Madrid"})
    # Use a non-dict, non-object slot to trigger unknown format
    state["nlu_result"] = {
        "message_type": "correction",
        "slots": ["invalid_format"],  # Not a dict, not an object with name
    }

    # Act
    result = await handle_correction_node(state, mock_runtime)

    # Assert
    assert result.get("conversation_state") == "error"


# === TESTS FOR EDGE CASES ===


@pytest.mark.asyncio
async def test_handle_correction_no_nlu_result(create_state_with_slots, mock_runtime):
    """Test that handle_correction handles absence of NLU result."""
    # Arrange
    state = create_state_with_slots("book_flight", slots={"origin": "Madrid"})
    state["nlu_result"] = None

    # Act
    result = await handle_correction_node(state, mock_runtime)

    # Assert
    assert result.get("conversation_state") == "error"


@pytest.mark.asyncio
async def test_handle_correction_no_slots(create_state_with_slots, mock_runtime):
    """Test that handle_correction handles absence of slots in NLU."""
    # Arrange
    state = create_state_with_slots("book_flight", slots={"origin": "Madrid"})
    state["nlu_result"] = {
        "message_type": "correction",
        "slots": [],  # No slots
    }

    # Act
    result = await handle_correction_node(state, mock_runtime)

    # Assert
    # Should return waiting_for_slot if flow is active
    assert result.get("conversation_state") in ("waiting_for_slot", "error")


@pytest.mark.asyncio
async def test_handle_correction_no_active_flow(mock_runtime):
    """Test that handle_correction handles absence of active flow."""
    # Arrange
    from soni.core.state import create_empty_state

    state = create_empty_state()
    # Create NLU result directly without using fixture
    from soni.du.models import NLUOutput

    nlu_result = NLUOutput(
        message_type=MessageType.CORRECTION,
        command="continue",
        slots=[SlotValue(name="destination", value="Barcelona", confidence=0.95)],
        confidence=0.95,
    )
    state["nlu_result"] = nlu_result.model_dump()

    # Mock no active flow
    mock_runtime.context["flow_manager"].get_active_context.return_value = None

    # Act
    result = await handle_correction_node(state, mock_runtime)

    # Assert
    assert result.get("conversation_state") == "error"


@pytest.mark.asyncio
async def test_handle_correction_normalization_failure(
    create_state_with_slots, mock_nlu_correction, mock_normalizer_failure
):
    """Test that handle_correction handles normalization failure."""
    # Arrange
    state = create_state_with_slots("book_flight", slots={"destination": "Madrid"})
    state["nlu_result"] = mock_nlu_correction.predict.return_value.model_dump()

    mock_runtime = MagicMock()
    mock_runtime.context = {
        "normalizer": mock_normalizer_failure,
        "flow_manager": MagicMock(),
        "step_manager": MagicMock(),
        "config": MagicMock(),
    }
    mock_runtime.context["flow_manager"].get_active_context.return_value = {
        "flow_id": "flow_1",
        "flow_name": "book_flight",
        "current_step": "collect_destination",
    }

    # Act
    result = await handle_correction_node(state, mock_runtime)

    # Assert
    assert result.get("conversation_state") == "error"


# === TESTS FOR ROUTING POST-CORRECTION ===


@pytest.mark.asyncio
async def test_handle_correction_returns_to_collect_step(
    create_state_with_slots, mock_nlu_correction, mock_runtime
):
    """Test that correction during collection returns to collect step."""
    # Arrange
    state = create_state_with_slots(
        "book_flight",
        slots={"origin": "Madrid"},
        current_step="collect_destination",
        conversation_state="waiting_for_slot",
    )
    state["nlu_result"] = mock_nlu_correction.predict.return_value.model_dump()

    # Mock step config
    from soni.core.config import StepConfig

    step_config = StepConfig(step="collect_destination", type="collect", slot="destination")
    mock_runtime.context["normalizer"].normalize_slot.return_value = "Barcelona"
    mock_runtime.context["flow_manager"].get_active_context.return_value = {
        "flow_id": "flow_1",
        "flow_name": "book_flight",
        "current_step": "collect_destination",
        "flow_state": "active",
    }
    mock_runtime.context["step_manager"].config = MagicMock()
    mock_runtime.context["step_manager"].config.flows = {}
    mock_runtime.context["step_manager"].get_current_step_config = MagicMock(
        return_value=step_config
    )

    # Act
    result = await handle_correction_node(state, mock_runtime)

    # Assert
    assert result["conversation_state"] == "waiting_for_slot"
    assert result["flow_stack"][0]["current_step"] == "collect_destination"


@pytest.mark.asyncio
async def test_handle_correction_returns_to_confirmation_step(
    create_state_with_slots, mock_nlu_correction, mock_runtime
):
    """Test that correction during confirmation returns to confirmation step."""
    # Arrange
    state = create_state_with_slots(
        "book_flight",
        slots={"origin": "Madrid", "destination": "Barcelona"},
        current_step="confirm_booking",
        conversation_state="confirming",
    )
    state["nlu_result"] = mock_nlu_correction.predict.return_value.model_dump()

    # Mock step config
    from soni.core.config import StepConfig

    step_config = StepConfig(step="confirm_booking", type="confirm", message="Confirm?")
    mock_runtime.context["normalizer"].normalize_slot.return_value = "Valencia"
    mock_runtime.context["flow_manager"].get_active_context.return_value = {
        "flow_id": "flow_1",
        "flow_name": "book_flight",
        "current_step": "confirm_booking",
        "flow_state": "active",
    }
    mock_runtime.context["step_manager"].config = MagicMock()
    mock_runtime.context["step_manager"].config.flows = {}
    mock_runtime.context["step_manager"].get_current_step_config = MagicMock(
        return_value=step_config
    )

    # Act
    result = await handle_correction_node(state, mock_runtime)

    # Assert
    assert result["conversation_state"] == "ready_for_confirmation"
    assert result["flow_stack"][0]["current_step"] == "confirm_booking"


@pytest.mark.asyncio
async def test_handle_correction_all_slots_filled_routes_to_confirmation(
    create_state_with_slots, mock_nlu_correction, mock_runtime
):
    """Test that correction with all slots filled routes to confirmation."""
    # Arrange
    state = create_state_with_slots(
        "book_flight",
        slots={"origin": "Madrid", "destination": "Barcelona", "date": "2025-12-25"},
        current_step="collect_date",
    )
    state["nlu_result"] = mock_nlu_correction.predict.return_value.model_dump()

    # Mock flow config with all slots
    from soni.core.config import FlowConfig, StepConfig, TriggerConfig

    flow_config = FlowConfig(
        description="Book flight",
        trigger=TriggerConfig(intents=[]),
        steps=[
            StepConfig(step="collect_origin", type="collect", slot="origin"),
            StepConfig(step="collect_destination", type="collect", slot="destination"),
            StepConfig(step="collect_date", type="collect", slot="date"),
            StepConfig(step="confirm_booking", type="confirm", message="Confirm?"),
        ],
    )

    mock_runtime.context["step_manager"].config = MagicMock()
    mock_runtime.context["step_manager"].config.flows = {"book_flight": flow_config}
    mock_runtime.context["normalizer"].normalize_slot.return_value = "Valencia"

    # Mock get_current_step_config to return confirm step when called with confirm_booking
    confirm_step_config = StepConfig(step="confirm_booking", type="confirm", message="Confirm?")
    collect_step_config = StepConfig(step="collect_date", type="collect", slot="date")

    def get_step_config_side_effect(state, context):
        # When all slots are filled, logic finds confirm_booking as target_step
        # and calls get_current_step_config with current_step="confirm_booking"
        current_step = state.get("current_step")
        if current_step == "confirm_booking":
            return confirm_step_config
        return collect_step_config

    mock_runtime.context["step_manager"].get_current_step_config = MagicMock(
        side_effect=get_step_config_side_effect
    )

    # Act
    result = await handle_correction_node(state, mock_runtime)

    # Assert
    # All slots are filled, so it should route to confirmation step
    assert result["conversation_state"] == "ready_for_confirmation"


# === TESTS FOR PREVIOUS STATES ===


@pytest.mark.asyncio
async def test_handle_correction_from_ready_for_action(
    create_state_with_slots, mock_nlu_correction, mock_runtime
):
    """Test correction from ready_for_action state."""
    # Arrange
    state = create_state_with_slots(
        "book_flight",
        slots={"origin": "Madrid", "destination": "Barcelona"},
        current_step="execute_booking",
        conversation_state="ready_for_action",
    )
    state["nlu_result"] = mock_nlu_correction.predict.return_value.model_dump()

    # Mock step config
    from soni.core.config import StepConfig

    step_config = StepConfig(step="execute_booking", type="action", call="book_flight")
    mock_runtime.context["normalizer"].normalize_slot.return_value = "Valencia"
    mock_runtime.context["step_manager"].config = MagicMock()
    mock_runtime.context["step_manager"].config.flows = {}
    mock_runtime.context["step_manager"].get_current_step_config = MagicMock(
        return_value=step_config
    )

    # Act
    result = await handle_correction_node(state, mock_runtime)

    # Assert
    assert result["conversation_state"] == "ready_for_action"


@pytest.mark.asyncio
async def test_handle_correction_from_ready_for_confirmation(
    create_state_with_slots, mock_nlu_correction, mock_runtime
):
    """Test correction from ready_for_confirmation state."""
    # Arrange
    state = create_state_with_slots(
        "book_flight",
        slots={"origin": "Madrid", "destination": "Barcelona"},
        current_step="confirm_booking",
        conversation_state="ready_for_confirmation",
    )
    state["nlu_result"] = mock_nlu_correction.predict.return_value.model_dump()

    # Mock step config
    from soni.core.config import StepConfig

    step_config = StepConfig(step="confirm_booking", type="confirm", message="Confirm?")
    mock_runtime.context["normalizer"].normalize_slot.return_value = "Valencia"
    mock_runtime.context["step_manager"].config = MagicMock()
    mock_runtime.context["step_manager"].config.flows = {}
    mock_runtime.context["step_manager"].get_current_step_config = MagicMock(
        return_value=step_config
    )

    # Act
    result = await handle_correction_node(state, mock_runtime)

    # Assert
    assert result["conversation_state"] == "ready_for_confirmation"


@pytest.mark.asyncio
async def test_handle_correction_from_confirming(
    create_state_with_slots, mock_nlu_correction, mock_runtime
):
    """Test correction from confirming state."""
    # Arrange
    state = create_state_with_slots(
        "book_flight",
        slots={"origin": "Madrid", "destination": "Barcelona"},
        current_step="confirm_booking",
        conversation_state="confirming",
    )
    state["nlu_result"] = mock_nlu_correction.predict.return_value.model_dump()

    # Mock step config
    from soni.core.config import StepConfig

    step_config = StepConfig(step="confirm_booking", type="confirm", message="Confirm?")
    mock_runtime.context["normalizer"].normalize_slot.return_value = "Valencia"
    mock_runtime.context["step_manager"].config = MagicMock()
    mock_runtime.context["step_manager"].config.flows = {}
    mock_runtime.context["step_manager"].get_current_step_config = MagicMock(
        return_value=step_config
    )

    # Act
    result = await handle_correction_node(state, mock_runtime)

    # Assert
    assert result["conversation_state"] == "ready_for_confirmation"


@pytest.mark.asyncio
async def test_handle_correction_from_waiting_for_slot(
    create_state_with_slots, mock_nlu_correction, mock_runtime
):
    """Test correction from waiting_for_slot state."""
    # Arrange
    state = create_state_with_slots(
        "book_flight",
        slots={"origin": "Madrid"},
        current_step="collect_destination",
        conversation_state="waiting_for_slot",
    )
    state["nlu_result"] = mock_nlu_correction.predict.return_value.model_dump()

    # Mock step config
    from soni.core.config import StepConfig

    step_config = StepConfig(step="collect_destination", type="collect", slot="destination")
    mock_runtime.context["normalizer"].normalize_slot.return_value = "Barcelona"
    mock_runtime.context["step_manager"].config = MagicMock()
    mock_runtime.context["step_manager"].config.flows = {}
    mock_runtime.context["step_manager"].get_current_step_config = MagicMock(
        return_value=step_config
    )

    # Act
    result = await handle_correction_node(state, mock_runtime)

    # Assert
    assert result["conversation_state"] == "waiting_for_slot"


# === TESTS FOR METADATA AND RESPONSE ===


@pytest.mark.asyncio
async def test_handle_correction_sets_metadata_flags(
    create_state_with_slots, mock_nlu_correction, mock_runtime
):
    """Test that handle_correction sets metadata flags correctly."""
    # Arrange
    state = create_state_with_slots("book_flight", slots={"destination": "Madrid"})
    state["nlu_result"] = mock_nlu_correction.predict.return_value.model_dump()

    mock_runtime.context["normalizer"].normalize_slot.return_value = "Barcelona"

    # Act
    result = await handle_correction_node(state, mock_runtime)

    # Assert
    assert result["metadata"]["_correction_slot"] == "destination"
    assert result["metadata"]["_correction_value"] == "Barcelona"
    assert "_modification_slot" not in result["metadata"]  # Should clear modification


@pytest.mark.asyncio
async def test_handle_correction_clears_modification_flags(
    create_state_with_slots, mock_nlu_correction, mock_runtime
):
    """Test that handle_correction clears modification flags."""
    # Arrange
    state = create_state_with_slots("book_flight", slots={"destination": "Madrid"})
    state["metadata"]["_modification_slot"] = "origin"
    state["nlu_result"] = mock_nlu_correction.predict.return_value.model_dump()

    mock_runtime.context["normalizer"].normalize_slot.return_value = "Barcelona"

    # Act
    result = await handle_correction_node(state, mock_runtime)

    # Assert
    assert "_modification_slot" not in result["metadata"]


@pytest.mark.asyncio
async def test_handle_correction_acknowledgment_message(
    create_state_with_slots, mock_nlu_correction, mock_runtime
):
    """Test that handle_correction generates acknowledgment message."""
    # Arrange
    state = create_state_with_slots("book_flight", slots={"destination": "Madrid"})
    state["nlu_result"] = mock_nlu_correction.predict.return_value.model_dump()

    mock_runtime.context["normalizer"].normalize_slot.return_value = "Barcelona"

    # Act
    result = await handle_correction_node(state, mock_runtime)

    # Assert
    assert "last_response" in result
    assert len(result["last_response"]) > 0
    # Message should contain acknowledgment
    assert any(
        word in result["last_response"].lower()
        for word in ["updated", "changed", "corrected", "got it"]
    )


# === TESTS FOR _get_response_template ===


def test_get_response_template_from_config_dict():
    """Test that _get_response_template gets template from config dict."""
    # Arrange
    config = MagicMock()
    config.responses = {
        "correction_acknowledged": {"default": "Updated {slot_name} to {new_value}"}
    }

    # Act
    result = _get_response_template(
        config,
        "correction_acknowledged",
        "Default message",
        slot_name="destination",
        new_value="Barcelona",
    )

    # Assert
    assert "destination" in result
    assert "Barcelona" in result


def test_get_response_template_from_config_string():
    """Test that _get_response_template gets template from config string."""
    # Arrange
    config = MagicMock()
    config.responses = {"correction_acknowledged": "Updated {slot_name} to {new_value}"}

    # Act
    result = _get_response_template(
        config,
        "correction_acknowledged",
        "Default message",
        slot_name="destination",
        new_value="Barcelona",
    )

    # Assert
    assert "destination" in result
    assert "Barcelona" in result


def test_get_response_template_default_fallback():
    """Test that _get_response_template uses default if no config."""
    # Arrange
    config = MagicMock()
    config.responses = {}

    # Act
    result = _get_response_template(config, "correction_acknowledged", "Default message")

    # Assert
    assert result == "Default message"


def test_get_response_template_interpolation_single_var():
    """Test that _get_response_template interpolates single variable."""
    # Arrange
    config = MagicMock()
    config.responses = {"correction_acknowledged": {"default": "Updated {slot_name}"}}

    # Act
    result = _get_response_template(
        config, "correction_acknowledged", "Default", slot_name="destination"
    )

    # Assert
    assert result == "Updated destination"


def test_get_response_template_interpolation_multiple_vars():
    """Test that _get_response_template interpolates multiple variables."""
    # Arrange
    config = MagicMock()
    config.responses = {
        "correction_acknowledged": {
            "default": "Updated {slot_name} from {old_value} to {new_value}"
        }
    }

    # Act
    result = _get_response_template(
        config,
        "correction_acknowledged",
        "Default",
        slot_name="destination",
        old_value="Madrid",
        new_value="Barcelona",
    )

    # Assert
    assert "destination" in result
    assert "Madrid" in result
    assert "Barcelona" in result


def test_get_response_template_missing_config():
    """Test that _get_response_template handles missing config gracefully."""
    # Arrange
    config = MagicMock()
    config.responses = None

    # Act
    result = _get_response_template(config, "correction_acknowledged", "Default message")

    # Assert
    assert result == "Default message"


# === TESTS FOR RE-PROMPT AFTER CORRECTION ===


@pytest.mark.asyncio
async def test_handle_correction_reprompts_next_slot(create_state_with_slots, mock_runtime):
    """Test that handle_correction re-prompts for next slot after correction."""
    # Arrange
    # Scenario: User corrects origin while waiting for destination
    state = create_state_with_slots(
        "book_flight",
        slots={"origin": "Chicago"},  # Original value
        current_step="collect_destination",  # Currently waiting for destination
    )

    # NLU detects correction of origin
    from soni.du.models import NLUOutput

    nlu_result = NLUOutput(
        message_type=MessageType.CORRECTION,
        command="continue",
        slots=[SlotValue(name="origin", value="Denver", confidence=0.95)],
        confidence=0.95,
    )
    state["nlu_result"] = nlu_result.model_dump()

    # Mock flow config
    from soni.core.config import FlowConfig, StepConfig, TriggerConfig

    flow_config = FlowConfig(
        description="Book flight",
        trigger=TriggerConfig(intents=[]),
        steps=[
            StepConfig(step="collect_origin", type="collect", slot="origin"),
            StepConfig(step="collect_destination", type="collect", slot="destination"),
            StepConfig(step="collect_date", type="collect", slot="date"),
        ],
    )

    mock_runtime.context["step_manager"].config = MagicMock()
    mock_runtime.context["step_manager"].config.flows = {"book_flight": flow_config}
    mock_runtime.context["normalizer"].normalize_slot.return_value = "Denver"

    # Mock get_current_step_config to return collect_origin step when called with origin
    origin_step_config = StepConfig(step="collect_origin", type="collect", slot="origin")
    destination_step_config = StepConfig(
        step="collect_destination", type="collect", slot="destination"
    )

    def get_step_config_side_effect(state, context):
        current_step = state.get("current_step")
        if current_step == "collect_origin":
            return origin_step_config
        elif current_step == "collect_destination":
            return destination_step_config
        return None

    mock_runtime.context["step_manager"].get_current_step_config = MagicMock(
        side_effect=get_step_config_side_effect
    )

    # Mock get_next_required_slot to return destination (next slot after origin)
    mock_runtime.context["step_manager"].get_next_required_slot = MagicMock(
        return_value="destination"
    )

    # Mock get_slot_config to return prompt for destination
    from unittest.mock import patch

    from soni.core.state import get_slot_config

    destination_slot_config = MagicMock()
    destination_slot_config.prompt = "Where would you like to go?"

    def get_slot_config_side_effect(context, slot_name):
        if slot_name == "destination":
            return destination_slot_config
        raise KeyError(f"Slot {slot_name} not found")

    # Patch get_slot_config in the module where it's used
    with patch("soni.core.state.get_slot_config", side_effect=get_slot_config_side_effect):
        # Act
        result = await handle_correction_node(state, mock_runtime)

    # Assert
    # Should update the slot
    assert result["flow_slots"]["flow_1"]["origin"] == "Denver"

    # Should return to collect_origin step (where the corrected slot belongs)
    assert result["current_step"] == "collect_origin"
    assert result["flow_stack"][0]["current_step"] == "collect_origin"

    # Should be in waiting_for_slot state
    assert result["conversation_state"] == "waiting_for_slot"

    # CRITICAL: Should include both acknowledgment AND next slot prompt
    last_response = result["last_response"]
    assert (
        "Got it, I've updated origin to Denver" in last_response
        or "updated origin to Denver" in last_response
    )
    assert "Where would you like to go?" in last_response or "destination" in last_response.lower()

    # Should set waiting_for_slot to destination
    assert result.get("waiting_for_slot") == "destination"


# === ADDITIONAL TESTS FOR COVERAGE >85% ===


@pytest.mark.asyncio
async def test_handle_correction_new_flow_id_creates_slots_dict(
    create_state_with_slots, mock_nlu_correction, mock_runtime
):
    """Test that correction with new flow_id creates flow_slots entry."""
    # Arrange - state without flow_id in flow_slots
    from soni.core.state import create_empty_state

    state = create_empty_state()
    state["flow_stack"] = [
        {
            "flow_id": "new_flow_1",
            "flow_name": "book_flight",
            "current_step": "collect_origin",
            "flow_state": "active",
            "started_at": 1702214400.0,
            "paused_at": None,
            "completed_at": None,
            "outputs": {},
            "context": None,
        }
    ]
    state["flow_slots"] = {}  # Empty, flow_id not present
    state["nlu_result"] = mock_nlu_correction.predict.return_value.model_dump()

    mock_runtime.context["normalizer"].normalize_slot.return_value = "Barcelona"
    mock_runtime.context["flow_manager"].get_active_context.return_value = {
        "flow_id": "new_flow_1",
        "flow_name": "book_flight",
        "current_step": "collect_origin",
    }
    mock_runtime.context["step_manager"].config = MagicMock()
    mock_runtime.context["step_manager"].config.flows = {}

    # Act
    result = await handle_correction_node(state, mock_runtime)

    # Assert
    assert "new_flow_1" in result["flow_slots"]
    assert result["flow_slots"]["new_flow_1"]["destination"] == "Barcelona"


@pytest.mark.asyncio
async def test_handle_correction_fallback_to_collect_step_for_slot(
    create_state_with_slots, mock_nlu_correction, mock_runtime
):
    """Test fallback to step that collects the corrected slot."""
    # Arrange
    state = create_state_with_slots("book_flight", slots={"origin": "Madrid"})
    state["nlu_result"] = mock_nlu_correction.predict.return_value.model_dump()
    # Remove current_step to trigger fallback
    state["flow_stack"][0]["current_step"] = None

    from soni.core.config import FlowConfig, StepConfig, TriggerConfig

    flow_config = FlowConfig(
        description="Book flight",
        trigger=TriggerConfig(intents=[]),
        steps=[
            StepConfig(step="collect_origin", type="collect", slot="origin"),
            StepConfig(step="collect_destination", type="collect", slot="destination"),
        ],
    )

    mock_runtime.context["normalizer"].normalize_slot.return_value = "Barcelona"
    mock_runtime.context["flow_manager"].get_active_context.return_value = {
        "flow_id": "flow_1",
        "flow_name": "book_flight",
        "current_step": None,
    }
    mock_runtime.context["step_manager"].config = MagicMock()
    mock_runtime.context["step_manager"].config.flows = {"book_flight": flow_config}
    mock_runtime.context["step_manager"].get_current_step_config = MagicMock(return_value=None)

    # Act
    result = await handle_correction_node(state, mock_runtime)

    # Assert - should fallback to collect_destination step or use fallback path
    # The fallback path finds the step that collects the slot
    if "flow_stack" in result:
        assert result["flow_stack"][0]["current_step"] == "collect_destination"
    else:
        # Fallback path doesn't return flow_stack, just updates slots
        assert result["flow_slots"]["flow_1"]["destination"] == "Barcelona"
        assert "last_response" in result


@pytest.mark.asyncio
async def test_handle_correction_fallback_when_no_target_step(
    create_state_with_slots, mock_nlu_correction, mock_runtime
):
    """Test fallback when no target step can be determined."""
    # Arrange
    state = create_state_with_slots("book_flight", slots={"origin": "Madrid"})
    state["nlu_result"] = mock_nlu_correction.predict.return_value.model_dump()
    state["flow_stack"][0]["current_step"] = None

    mock_runtime.context["normalizer"].normalize_slot.return_value = "Barcelona"
    mock_runtime.context["flow_manager"].get_active_context.return_value = {
        "flow_id": "flow_1",
        "flow_name": "book_flight",
        "current_step": None,
    }
    mock_runtime.context["step_manager"].config = MagicMock()
    mock_runtime.context["step_manager"].config.flows = {}  # No flow config
    mock_runtime.context["step_manager"].get_current_step_config = MagicMock(return_value=None)

    # Act
    result = await handle_correction_node(state, mock_runtime)

    # Assert - should use fallback
    # Fallback returns previous_conversation_state or "waiting_for_slot"
    assert "flow_slots" in result
    assert result["flow_slots"]["flow_1"]["destination"] == "Barcelona"
    assert "last_response" in result
    # When no target_step found, fallback returns previous_conversation_state or "waiting_for_slot"
    assert result["conversation_state"] == "waiting_for_slot"


@pytest.mark.asyncio
async def test_handle_correction_finds_step_from_conversation_state_confirming(
    create_state_with_slots, mock_nlu_correction, mock_runtime
):
    """Test finding step from conversation_state when confirming."""
    # Arrange
    state = create_state_with_slots(
        "book_flight",
        slots={"origin": "Madrid", "destination": "Barcelona"},
        current_step=None,  # No current step
        conversation_state="confirming",
    )
    state["nlu_result"] = mock_nlu_correction.predict.return_value.model_dump()

    from soni.core.config import FlowConfig, StepConfig, TriggerConfig

    flow_config = FlowConfig(
        description="Book flight",
        trigger=TriggerConfig(intents=[]),
        steps=[
            StepConfig(step="collect_origin", type="collect", slot="origin"),
            StepConfig(step="collect_destination", type="collect", slot="destination"),
            StepConfig(step="confirm_booking", type="confirm", message="Confirm?"),
        ],
    )

    step_config = StepConfig(step="confirm_booking", type="confirm", message="Confirm?")
    mock_runtime.context["normalizer"].normalize_slot.return_value = "Valencia"
    mock_runtime.context["flow_manager"].get_active_context.return_value = {
        "flow_id": "flow_1",
        "flow_name": "book_flight",
        "current_step": None,
    }
    mock_runtime.context["step_manager"].config = MagicMock()
    mock_runtime.context["step_manager"].config.flows = {"book_flight": flow_config}
    mock_runtime.context["step_manager"].get_current_step_config = MagicMock(
        return_value=step_config
    )

    # Act
    result = await handle_correction_node(state, mock_runtime)

    # Assert - should find confirm step from conversation_state
    assert result["flow_stack"][0]["current_step"] == "confirm_booking"
    assert result["conversation_state"] == "ready_for_confirmation"


@pytest.mark.asyncio
async def test_handle_correction_finds_step_from_conversation_state_action(
    create_state_with_slots, mock_nlu_correction, mock_runtime
):
    """Test finding step from conversation_state when ready_for_action."""
    # Arrange
    state = create_state_with_slots(
        "book_flight",
        slots={"origin": "Madrid", "destination": "Barcelona"},
        current_step=None,
        conversation_state="ready_for_action",
    )
    state["nlu_result"] = mock_nlu_correction.predict.return_value.model_dump()

    from soni.core.config import FlowConfig, StepConfig, TriggerConfig

    flow_config = FlowConfig(
        description="Book flight",
        trigger=TriggerConfig(intents=[]),
        steps=[
            StepConfig(step="collect_origin", type="collect", slot="origin"),
            StepConfig(step="collect_destination", type="collect", slot="destination"),
            StepConfig(step="execute_booking", type="action", call="book_flight"),
        ],
    )

    step_config = StepConfig(step="execute_booking", type="action", call="book_flight")
    mock_runtime.context["normalizer"].normalize_slot.return_value = "Valencia"
    mock_runtime.context["flow_manager"].get_active_context.return_value = {
        "flow_id": "flow_1",
        "flow_name": "book_flight",
        "current_step": None,
    }
    mock_runtime.context["step_manager"].config = MagicMock()
    mock_runtime.context["step_manager"].config.flows = {"book_flight": flow_config}
    mock_runtime.context["step_manager"].get_current_step_config = MagicMock(
        return_value=step_config
    )

    # Act
    result = await handle_correction_node(state, mock_runtime)

    # Assert - should find action step from conversation_state
    assert result["flow_stack"][0]["current_step"] == "execute_booking"
    assert result["conversation_state"] == "ready_for_action"
