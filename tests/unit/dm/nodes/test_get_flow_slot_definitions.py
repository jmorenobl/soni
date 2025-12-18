"""Tests for get_flow_slot_definitions helper."""

import pytest

from soni.core.config import (
    CollectStepConfig,
    ConfirmStepConfig,
    FlowConfig,
    SayStepConfig,
    SlotConfig,
    SoniConfig,
    StepConfig,
)
from soni.dm.nodes.understand import get_flow_slot_definitions
from soni.du.slot_extractor import SlotExtractionInput


class TestGetFlowSlotDefinitions:
    """Tests for get_flow_slot_definitions function."""

    def test_returns_empty_for_nonexistent_flow(self):
        """GIVEN config without flow WHEN get_flow_slot_definitions THEN returns empty."""
        config = SoniConfig(flows={})
        result = get_flow_slot_definitions(config, "nonexistent")
        assert result == []

    def test_returns_empty_for_flow_without_collect_steps(self):
        """GIVEN flow with only say steps WHEN get_flow_slot_definitions THEN returns empty."""
        config = SoniConfig(
            flows={
                "greet": FlowConfig(
                    description="Greeting",
                    steps=[SayStepConfig(step="say_hi", type="say", message="Hello")],
                )
            }
        )
        result = get_flow_slot_definitions(config, "greet")
        assert result == []

    def test_returns_slot_definitions_for_collect_steps(self):
        """GIVEN flow with collect steps and defined slots WHEN get_flow_slot_definitions THEN returns SlotExtractionInput."""
        config = SoniConfig(
            slots={
                "amount": SlotConfig(
                    type="float",
                    prompt="How much?",
                    description="Transfer amount",
                ),
                "beneficiary_name": SlotConfig(
                    type="string",
                    prompt="Who?",
                    description="Recipient name",
                    examples=["John", "Mary"],
                ),
            },
            flows={
                "transfer": FlowConfig(
                    description="Transfer money",
                    steps=[
                        CollectStepConfig(
                            step="get_recipient", type="collect", slot="beneficiary_name"
                        ),
                        CollectStepConfig(step="get_amount", type="collect", slot="amount"),
                        ConfirmStepConfig(step="confirm", type="confirm", slot="confirmed"),
                    ],
                )
            },
        )

        result = get_flow_slot_definitions(config, "transfer")

        assert len(result) == 2
        assert all(isinstance(s, SlotExtractionInput) for s in result)

        # Check slot names are correct
        slot_names = {s.name for s in result}
        assert slot_names == {"amount", "beneficiary_name"}

        # Check amount slot
        amount_slot = next(s for s in result if s.name == "amount")
        assert amount_slot.slot_type == "float"
        assert amount_slot.description == "Transfer amount"

        # Check beneficiary slot
        beneficiary_slot = next(s for s in result if s.name == "beneficiary_name")
        assert beneficiary_slot.slot_type == "string"
        assert beneficiary_slot.examples == ["John", "Mary"]

    def test_uses_prompt_as_description_fallback(self):
        """GIVEN slot without description WHEN get_flow_slot_definitions THEN uses prompt."""
        config = SoniConfig(
            slots={
                "amount": SlotConfig(type="float", prompt="How much to transfer?"),
            },
            flows={
                "transfer": FlowConfig(
                    description="Transfer money",
                    steps=[CollectStepConfig(step="get_amount", type="collect", slot="amount")],
                )
            },
        )

        result = get_flow_slot_definitions(config, "transfer")

        assert len(result) == 1
        assert result[0].description == "How much to transfer?"

    def test_handles_undefined_slots_gracefully(self):
        """GIVEN collect step with undefined slot WHEN get_flow_slot_definitions THEN uses minimal info."""
        config = SoniConfig(
            slots={},  # No slots defined
            flows={
                "transfer": FlowConfig(
                    description="Transfer money",
                    steps=[CollectStepConfig(step="get_amount", type="collect", slot="amount")],
                )
            },
        )

        result = get_flow_slot_definitions(config, "transfer")

        assert len(result) == 1
        assert result[0].name == "amount"
        assert result[0].slot_type == "string"  # Default
        assert "amount" in result[0].description

    def test_excludes_non_collect_slots(self):
        """GIVEN flow with confirm slot WHEN get_flow_slot_definitions THEN excludes it."""
        config = SoniConfig(
            slots={
                "amount": SlotConfig(type="float", prompt="Amount?"),
                "confirmed": SlotConfig(type="bool", prompt="Confirm?"),
            },
            flows={
                "transfer": FlowConfig(
                    description="Transfer money",
                    steps=[
                        CollectStepConfig(step="get_amount", type="collect", slot="amount"),
                        ConfirmStepConfig(step="ask_confirm", type="confirm", slot="confirmed"),
                    ],
                )
            },
        )

        result = get_flow_slot_definitions(config, "transfer")

        assert len(result) == 1
        assert result[0].name == "amount"
