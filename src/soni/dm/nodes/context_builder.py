"""Builder for constructing dialogue context for NLU."""

import logging
from typing import Literal

from soni.config.models import CollectStepConfig, SoniConfig
from soni.core.types import DialogueState
from soni.du.models import (
    CommandInfo,
    DialogueContext,
    FlowInfo,
    SlotDefinition,
    SlotValue,
)
from soni.du.slot_extractor import SlotExtractionInput
from soni.flow.manager import FlowManager
from soni.runtime.context import RuntimeContext

logger = logging.getLogger(__name__)


class DialogueContextBuilder:
    """Constructs dialogue context for NLU processing.

    Follows SRP: only responsible for building context objects.
    """

    def __init__(self, context: RuntimeContext) -> None:
        self._context = context

    def build(self, state: DialogueState) -> DialogueContext:
        """Build full dialogue context for NLU.

        Args:
            state: Current dialogue state

        Returns:
            Constructed DialogueContext
        """
        config = self._context.config
        fm = self._context.flow_manager

        flows_info = self._build_flows_info(config)
        commands_info = self._build_commands_info()

        active_ctx = fm.get_active_context(state)
        active_flow = active_ctx["flow_name"] if active_ctx else None

        expected_slot = self._get_expected_slot(state)

        # Build flow_slots from active flow's collect steps
        flow_slots_defs: list[SlotDefinition] = []
        if active_flow and active_flow in config.flows:
            for slot_input in self.get_slot_definitions(active_flow):
                flow_slots_defs.append(
                    SlotDefinition(
                        name=slot_input.name,
                        slot_type=slot_input.slot_type,
                        description=slot_input.description,
                        examples=slot_input.examples,
                    )
                )

        # Build current_slots from flow state
        current_slots = self._get_current_slots(state, fm)

        conversation_state: Literal["idle", "collecting", "confirming", "action_pending"] = "idle"
        if not active_flow:
            conversation_state = "idle"
        elif expected_slot:
            conversation_state = "collecting"
        else:
            conversation_state = "collecting"

        return DialogueContext(
            available_flows=flows_info,
            available_commands=commands_info,
            active_flow=active_flow,
            flow_slots=flow_slots_defs,
            current_slots=current_slots,
            expected_slot=expected_slot,
            conversation_state=conversation_state,
        )

    def _build_flows_info(self, config: SoniConfig) -> list[FlowInfo]:
        """Build flow information list."""
        return [
            FlowInfo(
                name=name,
                description=flow.description or name,
                trigger_intents=getattr(flow, "trigger_intents", None) or [],
            )
            for name, flow in config.flows.items()
        ]

    def _build_commands_info(self) -> list[CommandInfo]:
        """Build standard command information list."""
        return [
            CommandInfo(
                command_type="start_flow",
                description="Start a new flow. flow_name must match one of available_flows.name",
                required_fields=["flow_name"],
                example='{"type": "start_flow", "flow_name": "check_balance"}',
            ),
            CommandInfo(
                command_type="set_slot",
                description="Set a slot value when user provides information",
                required_fields=["slot", "value"],
                example='{"type": "set_slot", "slot": "account_type", "value": "checking"}',
            ),
            CommandInfo(command_type="cancel_flow", description="Cancel current flow"),
            CommandInfo(command_type="chitchat", description="Off-topic message"),
            CommandInfo(command_type="affirm", description="User confirms/agrees"),
            CommandInfo(command_type="deny", description="User denies/disagrees"),
        ]

    def _get_expected_slot(self, state: DialogueState) -> str | None:
        """Extract expected slot from pending task."""
        pending_task = state.get("_pending_task")
        if not pending_task:
            return None

        if isinstance(pending_task, dict):
            val = pending_task.get("slot")
            return val if isinstance(val, str) else None

        val = getattr(pending_task, "slot", None)
        return val if isinstance(val, str) else None

    def get_slot_definitions(self, flow_name: str) -> list[SlotExtractionInput]:
        """Extract slot definitions from flow config for SlotExtractor."""
        config = self._context.config
        if flow_name not in config.flows:
            return []

        flow_config = config.flows[flow_name]
        definitions_map = {}

        # 1. explicit slots from flow definition
        if flow_config.slots:
            for slot in flow_config.slots:
                definitions_map[slot.name] = SlotExtractionInput(
                    name=slot.name,
                    slot_type=slot.type or "string",
                    description=slot.description or f"Value for {slot.name}",
                    examples=[],
                )

        # 2. implicit slots from collect steps (fallback)
        for step in flow_config.steps:
            if isinstance(step, CollectStepConfig) and step.slot not in definitions_map:
                definitions_map[step.slot] = SlotExtractionInput(
                    name=step.slot,
                    slot_type="string",
                    description=step.message or f"Value for {step.slot}",
                    examples=[],
                )

        return list(definitions_map.values())

    def _get_current_slots(self, state: DialogueState, fm: FlowManager) -> list[SlotValue]:
        """Get current slot values from flow state."""
        active_ctx = fm.get_active_context(state)
        if not active_ctx:
            return []

        flow_id = active_ctx["flow_id"]
        flow_slots = state.get("flow_slots", {})
        if not flow_slots:
            return []

        slot_dict = flow_slots.get(flow_id, {})
        return [
            SlotValue(name=name, value=str(value) if value is not None else None)
            for name, value in slot_dict.items()
            if not name.startswith("_")
        ]
