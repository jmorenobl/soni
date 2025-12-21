"""Tests for FlowDelta type export and Protocol type safety."""

from dataclasses import fields
from typing import get_type_hints

import pytest

from soni.core.types import (
    DialogueState,
    FlowContext,
    FlowContextProvider,
    FlowDelta,
    FlowStackProvider,
    SlotProvider,
)


class TestFlowDeltaExport:
    """Tests verifying FlowDelta is properly exported from core/types."""

    def test_flowdelta_importable_from_core_types(self) -> None:
        """Test that FlowDelta can be imported from core/types."""
        from soni.core.types import FlowDelta

        assert FlowDelta is not None

    def test_flowdelta_is_dataclass(self) -> None:
        """Test that FlowDelta is a dataclass with expected fields."""
        field_names = {f.name for f in fields(FlowDelta)}
        assert "flow_stack" in field_names
        assert "flow_slots" in field_names

    def test_flowdelta_fields_are_optional(self) -> None:
        """Test that FlowDelta can be created with no arguments."""
        delta = FlowDelta()
        assert delta.flow_stack is None
        assert delta.flow_slots is None

    def test_flowdelta_accepts_flow_stack(self) -> None:
        """Test FlowDelta with flow_stack argument."""
        stack: list[FlowContext] = []
        delta = FlowDelta(flow_stack=stack)
        assert delta.flow_stack == stack

    def test_flowdelta_accepts_flow_slots(self) -> None:
        """Test FlowDelta with flow_slots argument."""
        slots: dict[str, dict[str, object]] = {"flow_1": {"name": "test"}}
        delta = FlowDelta(flow_slots=slots)
        assert delta.flow_slots == slots


class TestProtocolReturnTypes:
    """Tests verifying Protocols use FlowDelta instead of Any."""

    def test_slot_provider_set_slot_returns_flowdelta(self) -> None:
        """Test SlotProvider.set_slot returns FlowDelta | None, not Any."""
        hints = get_type_hints(SlotProvider.set_slot)
        return_type = hints.get("return")

        assert return_type is not None
        # Check it contains FlowDelta (handles Union types)
        assert "FlowDelta" in str(return_type) or return_type == FlowDelta | None

    def test_flow_stack_provider_push_flow_returns_flowdelta(self) -> None:
        """Test FlowStackProvider.push_flow returns tuple[str, FlowDelta]."""
        hints = get_type_hints(FlowStackProvider.push_flow)
        return_type = hints.get("return")

        assert return_type is not None
        assert "FlowDelta" in str(return_type)

    def test_flow_stack_provider_pop_flow_returns_flowdelta(self) -> None:
        """Test FlowStackProvider.pop_flow returns tuple[FlowContext, FlowDelta]."""
        hints = get_type_hints(FlowStackProvider.pop_flow)
        return_type = hints.get("return")

        assert return_type is not None
        assert "FlowDelta" in str(return_type)

    def test_flow_stack_provider_handle_intent_change_returns_flowdelta(self) -> None:
        """Test FlowStackProvider.handle_intent_change returns FlowDelta | None."""
        hints = get_type_hints(FlowStackProvider.handle_intent_change)
        return_type = hints.get("return")

        assert return_type is not None
        assert "FlowDelta" in str(return_type) or return_type == FlowDelta | None

    def test_flow_context_provider_advance_step_returns_flowdelta(self) -> None:
        """Test FlowContextProvider.advance_step returns FlowDelta | None."""
        hints = get_type_hints(FlowContextProvider.advance_step)
        return_type = hints.get("return")

        assert return_type is not None
        assert "FlowDelta" in str(return_type) or return_type == FlowDelta | None


class TestFlowManagerImplementsProtocols:
    """Tests verifying FlowManager still implements protocols correctly."""

    def test_flow_manager_is_slot_provider(self) -> None:
        """Test FlowManager implements SlotProvider protocol."""
        from soni.flow.manager import FlowManager

        assert isinstance(FlowManager(), SlotProvider)

    def test_flow_manager_is_flow_stack_provider(self) -> None:
        """Test FlowManager implements FlowStackProvider protocol."""
        from soni.flow.manager import FlowManager

        assert isinstance(FlowManager(), FlowStackProvider)

    def test_flow_manager_is_flow_context_provider(self) -> None:
        """Test FlowManager implements FlowContextProvider protocol."""
        from soni.flow.manager import FlowManager

        assert isinstance(FlowManager(), FlowContextProvider)


class TestBackwardsCompatibility:
    """Tests for backwards compatibility of imports."""

    def test_flowdelta_importable_from_manager(self) -> None:
        """Test FlowDelta can still be imported from flow.manager."""
        from soni.flow.manager import FlowDelta

        assert FlowDelta is not None

    def test_merge_delta_still_works(self) -> None:
        """Test merge_delta function works with FlowDelta."""
        from soni.flow.manager import FlowDelta, merge_delta

        updates: dict[str, object] = {}
        delta = FlowDelta(flow_slots={"flow_1": {"key": "value"}})
        merge_delta(updates, delta)

        assert "flow_slots" in updates
