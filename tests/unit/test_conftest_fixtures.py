"""Optional tests to validate that conftest fixtures work correctly."""

from unittest.mock import AsyncMock

import pytest

from soni.du.models import MessageType
from tests.unit.conftest import StateBuilder


def test_create_nlu_mock_returns_correct_type(create_nlu_mock):
    """Test that create_nlu_mock returns AsyncMock."""
    nlu = create_nlu_mock(MessageType.SLOT_VALUE)
    assert isinstance(nlu, AsyncMock)


def test_create_state_with_flow_creates_valid_state(create_state_with_flow):
    """Test that create_state_with_flow creates valid state."""
    state = create_state_with_flow("book_flight")
    assert state["flow_stack"][0]["flow_name"] == "book_flight"
    assert "flow_1" in state["flow_slots"]


def test_state_builder_fluent_api():
    """Test that StateBuilder allows fluent API."""
    state = StateBuilder().with_flow("book_flight").with_slots({"origin": "Madrid"}).build()
    assert state["flow_slots"]["flow_1"]["origin"] == "Madrid"


def test_mock_nlu_slot_value(mock_nlu_slot_value):
    """Test that mock_nlu_slot_value fixture works."""
    result = mock_nlu_slot_value.predict.return_value
    assert result.message_type == MessageType.SLOT_VALUE
    assert len(result.slots) == 1
    assert result.slots[0].name == "origin"


def test_mock_nlu_correction(mock_nlu_correction):
    """Test that mock_nlu_correction fixture works."""
    result = mock_nlu_correction.predict.return_value
    assert result.message_type == MessageType.CORRECTION
    assert len(result.slots) == 1
    assert result.slots[0].name == "destination"


def test_mock_nlu_modification(mock_nlu_modification):
    """Test that mock_nlu_modification fixture works."""
    result = mock_nlu_modification.predict.return_value
    assert result.message_type == MessageType.MODIFICATION
    assert len(result.slots) == 1


def test_mock_nlu_confirmation_yes(mock_nlu_confirmation_yes):
    """Test that mock_nlu_confirmation_yes fixture works."""
    result = mock_nlu_confirmation_yes.predict.return_value
    assert result.message_type == MessageType.CONFIRMATION
    assert result.confirmation_value is True


def test_mock_nlu_confirmation_no(mock_nlu_confirmation_no):
    """Test that mock_nlu_confirmation_no fixture works."""
    result = mock_nlu_confirmation_no.predict.return_value
    assert result.message_type == MessageType.CONFIRMATION
    assert result.confirmation_value is False


def test_mock_nlu_confirmation_unclear(mock_nlu_confirmation_unclear):
    """Test that mock_nlu_confirmation_unclear fixture works."""
    result = mock_nlu_confirmation_unclear.predict.return_value
    assert result.message_type == MessageType.CONFIRMATION
    assert result.confirmation_value is None


def test_create_state_with_slots(create_state_with_slots):
    """Test that create_state_with_slots creates state with slots."""
    state = create_state_with_slots(
        "book_flight", slots={"origin": "Madrid", "destination": "Barcelona"}
    )
    assert state["flow_slots"]["flow_1"]["origin"] == "Madrid"
    assert state["flow_slots"]["flow_1"]["destination"] == "Barcelona"


def test_mock_runtime(mock_runtime):
    """Test that mock_runtime has all required dependencies."""
    assert hasattr(mock_runtime, "context")
    assert "flow_manager" in mock_runtime.context
    assert "step_manager" in mock_runtime.context
    assert "normalizer" in mock_runtime.context
    assert "config" in mock_runtime.context


@pytest.mark.asyncio
async def test_mock_normalizer_success(mock_normalizer_success):
    """Test that mock_normalizer_success works."""
    result = await mock_normalizer_success.normalize_slot("origin", "Madrid")
    assert result == "Madrid"


@pytest.mark.asyncio
async def test_mock_normalizer_failure(mock_normalizer_failure):
    """Test that mock_normalizer_failure raises error."""
    with pytest.raises(ValueError, match="Normalization failed"):
        await mock_normalizer_failure.normalize_slot("origin", "Madrid")


def test_mock_flow_config_complete(mock_flow_config_complete):
    """Test that mock_flow_config_complete has all steps."""
    assert mock_flow_config_complete.steps is not None
    assert len(mock_flow_config_complete.steps) == 5


def test_mock_flow_config_factory(mock_flow_config):
    """Test that mock_flow_config factory works."""
    config = mock_flow_config(
        "test_flow", steps=[{"step": "step1", "type": "collect", "slot": "slot1"}]
    )
    assert config.description == "Test flow"
    assert len(config.steps) == 1
    assert config.steps[0].step == "step1"
