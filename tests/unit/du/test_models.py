import pytest

from soni.core.commands import SetSlot, StartFlow
from soni.du.models import (
    CommandInfo,
    DialogueContext,
    FlowInfo,
    NLUOutput,
    SlotDefinition,
    SlotValue,
)


class TestNLUModels:
    """Tests for NLU Pydantic models and their string representations."""

    def test_flow_info_str(self):
        flow = FlowInfo(name="test", description="desc", trigger_intents=["hi"])
        s = str(flow)
        assert "test: desc" in s
        assert "Trigger intents: hi" in s

    def test_slot_value_str(self):
        slot = SlotValue(name="amount", value="100", expected_type="number")
        s = str(slot)
        assert "amount='100' (number)" in s

        slot_none = SlotValue(name="msg", value=None)
        assert "msg=None" in str(slot_none)

    def test_slot_definition_str(self):
        sd = SlotDefinition(
            name="city",
            slot_type="string",
            description="target city",
            required=True,
            examples=["London", "Paris"],
        )
        s = str(sd)
        assert "city (string, required): target city" in s
        assert "e.g., London, Paris" in s

    def test_command_info_str(self):
        ci = CommandInfo(
            command_type="start_flow",
            description="starts a flow",
            required_fields=["flow_name"],
            example="book a flight",
        )
        s = str(ci)
        assert "start_flow: starts a flow" in s
        assert "[Required: flow_name]" in s
        assert "'book a flight'" in s

    def test_dialogue_context_str(self):
        ctx = DialogueContext(
            available_flows=[FlowInfo(name="f1", description="d1")],
            available_commands=[CommandInfo(command_type="c1", description="d1")],
            active_flow="f1",
            expected_slot="s1",
            conversation_state="collecting",
            flow_slots=[SlotDefinition(name="s1", slot_type="str", description="d")],
            current_slots=[SlotValue(name="s2", value="v2")],
        )
        s = str(ctx)
        assert "CONTEXT:" in s
        assert "State: collecting" in s
        assert "Active Flow: f1" in s
        assert "Expected Slot: s1" in s
        assert "Flow Slots" in s
        assert "Current Slots" in s
        assert "Available Flows" in s
        assert "Available Commands" in s

    def test_nlu_output_validation(self):
        """Should validate NLUOutput with multiple command types."""
        output = NLUOutput(
            commands=[StartFlow(flow_name="order_pizza"), SetSlot(slot="size", value="large")],
            confidence=0.9,
        )
        assert len(output.commands) == 2
        assert isinstance(output.commands[0], StartFlow)
        assert isinstance(output.commands[1], SetSlot)
        assert output.confidence == 0.9
