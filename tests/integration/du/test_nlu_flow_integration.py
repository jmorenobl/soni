from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from soni.core.commands import SetSlot, StartFlow
from soni.core.state import create_empty_state
from soni.du.models import DialogueContext, NLUOutput
from soni.du.modules.extract_commands import CommandGenerator
from soni.du.modules.extract_slots import SlotExtractor
from soni.du.schemas.extract_slots import SlotExtractionInput, SlotExtractionResult
from soni.flow.manager import FlowManager


class TestNLUFlowIntegration:
    """Integration style tests for NLU and Flow Manager interaction."""

    @pytest.mark.asyncio
    async def test_full_nlu_flow_cycle(self, mock_llm):
        """Should simulate Pass 1 -> Flow Push -> Pass 2 -> Slot Update."""

        # 1. Setup
        state = create_empty_state()
        manager = FlowManager()

        # Mock Pass 1: Command Generator
        cmd_gen = CommandGenerator()
        cmd_gen.extractor = AsyncMock()

        mock_nlu_output = NLUOutput(
            commands=[StartFlow(flow_name="transfer_funds")], confidence=0.9
        )

        # Mocking dspy Prediction object
        mock_pred1 = MagicMock()
        mock_pred1.result = mock_nlu_output
        cmd_gen.extractor.acall.return_value = mock_pred1

        # 2. Pass 1: Intent Detection
        # We need to provide context
        context = DialogueContext(available_flows=[], available_commands=[])
        result1 = await cmd_gen.aforward("I want to send money", context)

        # 3. Process Pass 1 Commands
        from soni.flow.manager import apply_delta_to_dict

        for cmd in result1.commands:
            if isinstance(cmd, StartFlow):
                _, delta = manager.push_flow(state, cmd.flow_name)
                apply_delta_to_dict(state, delta)

        assert state["flow_stack"][-1]["flow_name"] == "transfer_funds"

        # 4. Mock Pass 2: Slot Extraction
        slot_extractor = SlotExtractor()
        slot_extractor.extractor = AsyncMock()

        extraction_data = SlotExtractionResult(extracted_slots=[SetSlot(slot="amount", value=100)])

        mock_pred2 = MagicMock()
        mock_pred2.result = "dummy"
        slot_extractor.extractor.acall.return_value = mock_pred2

        slot_defs = [SlotExtractionInput(name="amount", slot_type="number")]

        with patch(
            "soni.du.modules.extract_slots.safe_extract_result", return_value=extraction_data
        ):
            # 5. Pass 2: Slot Extraction
            result2 = await slot_extractor.aforward("Transfer 100", slot_defs)

        # 6. Apply Slots
        for cmd in result2:
            if isinstance(cmd, SetSlot):
                delta = manager.set_slot(state, cmd.slot, cmd.value)
                apply_delta_to_dict(state, delta)

        # 7. Final Verification
        active_id = manager.get_active_flow_id(state)
        assert active_id is not None
        assert state["flow_slots"][active_id]["amount"] == 100
