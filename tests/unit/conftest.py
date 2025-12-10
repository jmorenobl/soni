"""Common fixtures for unit tests."""

from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from soni.core.state import create_empty_state
from soni.core.types import DialogueState
from soni.du.models import MessageType, NLUOutput, SlotValue

# === NLU MOCKING FIXTURES ===


@pytest.fixture
def create_nlu_mock():
    """
    Factory fixture to create NLU mocks with specific message_type.

    Usage:
        def test_something(create_nlu_mock):
            nlu = create_nlu_mock(MessageType.SLOT_VALUE, slots=[...])
    """

    def _create(message_type: MessageType, **kwargs):
        nlu = AsyncMock()
        nlu.predict.return_value = NLUOutput(
            message_type=message_type,
            command=kwargs.get("command", "continue"),
            slots=kwargs.get("slots", []),
            confidence=kwargs.get("confidence", 0.95),
            confirmation_value=kwargs.get("confirmation_value"),
            reasoning=kwargs.get("reasoning", "Mocked NLU response"),
        )
        return nlu

    return _create


@pytest.fixture
def mock_nlu_slot_value():
    """Mock NLU returning SLOT_VALUE message type."""
    nlu = AsyncMock()
    nlu.predict.return_value = NLUOutput(
        message_type=MessageType.SLOT_VALUE,
        command="continue",
        slots=[SlotValue(name="origin", value="Madrid", confidence=0.95)],
        confidence=0.95,
        reasoning="User provided slot value",
    )
    return nlu


@pytest.fixture
def mock_nlu_correction():
    """Mock NLU returning CORRECTION message type."""
    nlu = AsyncMock()
    nlu.predict.return_value = NLUOutput(
        message_type=MessageType.CORRECTION,
        command="continue",
        slots=[SlotValue(name="destination", value="Barcelona", confidence=0.95)],
        confidence=0.95,
        reasoning="User is correcting a slot",
    )
    return nlu


@pytest.fixture
def mock_nlu_modification():
    """Mock NLU returning MODIFICATION message type."""
    nlu = AsyncMock()
    nlu.predict.return_value = NLUOutput(
        message_type=MessageType.MODIFICATION,
        command="continue",
        slots=[SlotValue(name="destination", value="Valencia", confidence=0.95)],
        confidence=0.95,
        reasoning="User is modifying a slot",
    )
    return nlu


@pytest.fixture
def mock_nlu_confirmation_yes():
    """Mock NLU returning YES confirmation."""
    nlu = AsyncMock()
    nlu.predict.return_value = NLUOutput(
        message_type=MessageType.CONFIRMATION,
        command="continue",
        confirmation_value=True,
        confidence=0.95,
        reasoning="User confirmed with yes",
    )
    return nlu


@pytest.fixture
def mock_nlu_confirmation_no():
    """Mock NLU returning NO confirmation."""
    nlu = AsyncMock()
    nlu.predict.return_value = NLUOutput(
        message_type=MessageType.CONFIRMATION,
        command="continue",
        confirmation_value=False,
        confidence=0.95,
        reasoning="User denied with no",
    )
    return nlu


@pytest.fixture
def mock_nlu_confirmation_unclear():
    """Mock NLU returning UNCLEAR confirmation."""
    nlu = AsyncMock()
    nlu.predict.return_value = NLUOutput(
        message_type=MessageType.CONFIRMATION,
        command="continue",
        confirmation_value=None,
        confidence=0.50,
        reasoning="Unclear confirmation response",
    )
    return nlu


@pytest.fixture
def mock_nlu_intent_change():
    """Mock NLU returning INTENT_CHANGE message type."""
    nlu = AsyncMock()
    nlu.predict.return_value = NLUOutput(
        message_type=MessageType.INTERRUPTION,
        command="book_hotel",
        slots=[],
        confidence=0.95,
        reasoning="User wants to change to a new flow",
    )
    return nlu


@pytest.fixture
def mock_nlu_digression():
    """Mock NLU returning QUESTION/HELP message type."""
    nlu = AsyncMock()
    nlu.predict.return_value = NLUOutput(
        message_type=MessageType.DIGRESSION,
        command="help",
        slots=[],
        confidence=0.90,
        reasoning="User asked a question",
    )
    return nlu


# === STATE CREATION FIXTURES ===


@pytest.fixture
def create_state_with_flow():
    """
    Factory fixture to create a state with an active flow.

    Usage:
        def test_something(create_state_with_flow):
            state = create_state_with_flow("book_flight", current_step="collect_origin")
    """

    def _create(flow_name: str, flow_id: str = "flow_1", **kwargs):
        state = create_empty_state()
        state["flow_stack"] = [
            {
                "flow_id": flow_id,
                "flow_name": flow_name,
                "current_step": kwargs.get("current_step", "collect_slot"),
                "flow_state": kwargs.get("flow_state", "active"),
                "started_at": 1702214400.0,
                "paused_at": None,
                "completed_at": None,
                "outputs": {},
                "context": None,
            }
        ]
        state["flow_slots"] = {flow_id: kwargs.get("slots", {})}
        state["conversation_state"] = kwargs.get("conversation_state", "waiting_for_slot")
        state["metadata"] = kwargs.get("metadata", {})
        return state

    return _create


@pytest.fixture
def create_state_with_slots():
    """
    Factory fixture to create a state with pre-filled slots.

    Usage:
        def test_something(create_state_with_slots):
            state = create_state_with_slots(
                "book_flight",
                slots={"origin": "Madrid", "destination": "Barcelona"}
            )
    """

    def _create(flow_name: str, slots: dict, flow_id: str = "flow_1", **kwargs):
        state = create_empty_state()
        state["flow_stack"] = [
            {
                "flow_id": flow_id,
                "flow_name": flow_name,
                "current_step": kwargs.get("current_step", "collect_slot"),
                "flow_state": "active",
                "started_at": 1702214400.0,
                "paused_at": None,
                "completed_at": None,
                "outputs": {},
                "context": None,
            }
        ]
        state["flow_slots"] = {flow_id: slots.copy()}
        state["conversation_state"] = kwargs.get("conversation_state", "waiting_for_slot")
        state["metadata"] = kwargs.get("metadata", {})
        return state

    return _create


# === RUNTIME/CONTEXT MOCKING FIXTURES ===


@pytest.fixture
def mock_runtime():
    """
    Mock NodeRuntime with all dependencies.

    Usage:
        async def test_something(mock_runtime):
            result = await some_node(state, mock_runtime)
    """
    runtime = MagicMock()

    # Mock flow_manager
    mock_flow_manager = MagicMock()
    mock_flow_manager.get_active_context.return_value = {
        "flow_id": "flow_1",
        "flow_name": "book_flight",
        "current_step": "collect_origin",
        "flow_state": "active",
    }

    # Mock step_manager
    mock_step_manager = MagicMock()
    mock_step_manager.advance_to_next_step.return_value = {
        "flow_stack": [],
        "conversation_state": "waiting_for_slot",
    }

    # Mock normalizer
    mock_normalizer = AsyncMock()
    mock_normalizer.normalize_slot.return_value = "normalized_value"

    # Mock config
    mock_config = MagicMock()
    mock_config.flows = {}
    mock_config.responses = {}

    # Assemble context
    runtime.context = {
        "flow_manager": mock_flow_manager,
        "step_manager": mock_step_manager,
        "normalizer": mock_normalizer,
        "config": mock_config,
    }

    return runtime


@pytest.fixture
def mock_normalizer_success():
    """Mock normalizer that always succeeds."""
    normalizer = AsyncMock()

    async def _normalize(slot_name: str, value: Any) -> Any:
        return value

    normalizer.normalize_slot = _normalize
    return normalizer


@pytest.fixture
def mock_normalizer_failure():
    """Mock normalizer that always fails."""
    normalizer = AsyncMock()

    async def _normalize(slot_name: str, value: Any) -> Any:
        raise ValueError("Normalization failed")

    normalizer.normalize_slot = _normalize
    return normalizer


# === HELPER FUNCTIONS ===


def create_state_with_correction_context(
    slot_to_correct: str, old_value: str, new_value: str
) -> DialogueState:
    """
    Helper para crear estado preparado para corrección.

    Usage:
        state = create_state_with_correction_context(
            "destination", "Madrid", "Barcelona"
        )
    """
    state = create_empty_state()
    state["flow_stack"] = [
        {
            "flow_id": "flow_1",
            "flow_name": "book_flight",
            "current_step": "collect_slot",
            "flow_state": "active",
            "started_at": 1702214400.0,
            "paused_at": None,
            "completed_at": None,
            "outputs": {},
            "context": None,
        }
    ]
    state["flow_slots"] = {"flow_1": {slot_to_correct: old_value}}
    state["nlu_result"] = {
        "message_type": "correction",
        "command": "continue",
        "slots": [{"name": slot_to_correct, "value": new_value}],
        "confidence": 0.95,
    }
    return state


def create_state_ready_for_confirmation(
    slots: dict, flow_name: str = "book_flight"
) -> DialogueState:
    """
    Helper para crear estado listo para confirmación.

    Usage:
        state = create_state_ready_for_confirmation({
            "origin": "Madrid",
            "destination": "Barcelona"
        })
    """
    state = create_empty_state()
    state["flow_stack"] = [
        {
            "flow_id": "flow_1",
            "flow_name": flow_name,
            "current_step": "confirm_booking",
            "flow_state": "active",
            "started_at": 1702214400.0,
            "paused_at": None,
            "completed_at": None,
            "outputs": {},
            "context": None,
        }
    ]
    state["flow_slots"] = {"flow_1": slots.copy()}
    state["conversation_state"] = "ready_for_confirmation"
    return state


# === STATE BUILDER PATTERN ===


class StateBuilder:
    """
    Builder pattern para crear estados complejos de forma fluida.

    Usage:
        state = (StateBuilder()
            .with_flow("book_flight")
            .with_slots({"origin": "Madrid"})
            .with_current_step("collect_destination")
            .with_metadata({"_confirmation_attempts": 1})
            .build())
    """

    def __init__(self):
        self.state = create_empty_state()

    def with_flow(self, flow_name: str, flow_id: str = "flow_1"):
        """Add a flow to the state."""
        self.state["flow_stack"] = [
            {
                "flow_id": flow_id,
                "flow_name": flow_name,
                "current_step": "collect_slot",
                "flow_state": "active",
                "started_at": 1702214400.0,
                "paused_at": None,
                "completed_at": None,
                "outputs": {},
                "context": None,
            }
        ]
        self.state["flow_slots"] = {flow_id: {}}
        return self

    def with_slots(self, slots: dict, flow_id: str = "flow_1"):
        """Add slots to the state."""
        if flow_id not in self.state["flow_slots"]:
            self.state["flow_slots"][flow_id] = {}
        self.state["flow_slots"][flow_id].update(slots)
        return self

    def with_current_step(self, step: str):
        """Set the current step."""
        if self.state["flow_stack"]:
            self.state["flow_stack"][-1]["current_step"] = step
        return self

    def with_conversation_state(self, conv_state: str):
        """Set the conversation state."""
        self.state["conversation_state"] = conv_state
        return self

    def with_metadata(self, metadata: dict):
        """Add metadata to the state."""
        self.state["metadata"] = metadata.copy()
        return self

    def with_nlu_result(self, nlu_result: dict):
        """Add NLU result to the state."""
        self.state["nlu_result"] = nlu_result
        return self

    def build(self):
        """Build and return the final state."""
        return self.state


# === CONFIGURATION MOCKING FIXTURES ===


@pytest.fixture
def mock_flow_config_complete():
    """
    Mock flow config con steps completos para testing.

    Útil para tests que necesitan verificar routing entre steps.

    Usage:
        def test_something(mock_flow_config_complete):
            config = mock_flow_config_complete
            assert len(config.steps) == 4
    """
    from soni.core.config import FlowConfig, StepConfig, TriggerConfig

    return FlowConfig(
        description="Book a flight",
        trigger=TriggerConfig(intents=["I want to book a flight"]),
        steps=[
            StepConfig(step="collect_origin", type="collect", slot="origin"),
            StepConfig(step="collect_destination", type="collect", slot="destination"),
            StepConfig(step="collect_date", type="collect", slot="date"),
            StepConfig(
                step="confirm_booking",
                type="confirm",
                message="Confirm: {origin} to {destination} on {date}?",
            ),
            StepConfig(step="execute_booking", type="action", call="book_flight_action"),
        ],
    )


@pytest.fixture
def mock_flow_config():
    """
    Factory fixture to create mock flow configurations.

    Usage:
        def test_something(mock_flow_config):
            config = mock_flow_config("book_flight", steps=[...])
    """

    def _create(flow_name: str, steps: list, description: str = "Test flow"):
        from soni.core.config import FlowConfig, StepConfig, TriggerConfig

        step_configs = []
        for step_data in steps:
            step_configs.append(
                StepConfig(
                    step=step_data.get("step", "step_1"),
                    type=step_data.get("type", "collect"),
                    slot=step_data.get("slot"),
                    message=step_data.get("message"),
                    call=step_data.get("call"),
                )
            )

        return FlowConfig(
            description=description, trigger=TriggerConfig(intents=[]), steps=step_configs
        )

    return _create
