"""Tests for slot utilities."""

import pytest

from soni.core.slot_utils import (
    deep_merge_flow_slots,
    get_slot_value,
    set_slot_value,
)


class TestDeepMergeFlowSlots:
    """Tests for deep_merge_flow_slots function."""

    def test_merge_empty_new_returns_base(self):
        """Test merging empty new dict returns base unchanged."""
        base = {"flow1": {"slot": "value"}}
        result = deep_merge_flow_slots(base, {})
        assert result == base
        assert result is not base  # Should be a copy

    def test_merge_empty_base_returns_new(self):
        """Test merging into empty base returns copy of new."""
        new = {"flow1": {"slot": "value"}}
        result = deep_merge_flow_slots({}, new)
        assert result == new
        assert result is not new

    def test_merge_adds_new_flow_ids(self):
        """Test that new flow_ids are added."""
        base = {"flow1": {"slot1": "a"}}
        new = {"flow2": {"slot2": "b"}}
        result = deep_merge_flow_slots(base, new)
        assert "flow1" in result
        assert "flow2" in result

    def test_merge_combines_slots_for_same_flow(self):
        """Test slots are merged for same flow_id."""
        base = {"flow1": {"slot_a": 1}}
        new = {"flow1": {"slot_b": 2}}
        result = deep_merge_flow_slots(base, new)
        assert result["flow1"] == {"slot_a": 1, "slot_b": 2}

    def test_merge_new_overwrites_existing_slot(self):
        """Test new slot values overwrite existing."""
        base = {"flow1": {"slot": "old"}}
        new = {"flow1": {"slot": "new"}}
        result = deep_merge_flow_slots(base, new)
        assert result["flow1"]["slot"] == "new"

    def test_merge_does_not_mutate_base_by_default(self):
        """Test base is not mutated when in_place=False."""
        base = {"flow1": {"slot": "value"}}
        original_base = {"flow1": {"slot": "value"}}
        deep_merge_flow_slots(base, {"flow1": {"new": "value"}})
        assert base == original_base

    def test_merge_mutates_base_when_in_place(self):
        """Test base is mutated when in_place=True."""
        base = {"flow1": {"slot": "value"}}
        result = deep_merge_flow_slots(base, {"flow1": {"new": "x"}}, in_place=True)
        assert base is result
        assert "new" in base["flow1"]

    def test_none_values_overwrite(self):
        """Test None values in new overwrite base values."""
        base = {"flow1": {"slot": "value"}}
        new = {"flow1": {"slot": None}}
        result = deep_merge_flow_slots(base, new)
        assert result["flow1"]["slot"] is None


class TestGetSlotValue:
    """Tests for get_slot_value function."""

    def test_returns_value_when_exists(self):
        """Test returns slot value when present."""
        slots = {"flow1": {"my_slot": "value"}}
        assert get_slot_value(slots, "flow1", "my_slot") == "value"

    def test_returns_default_when_flow_missing(self):
        """Test returns default when flow_id not found."""
        slots = {"flow1": {"slot": "value"}}
        assert get_slot_value(slots, "flow2", "slot", "default") == "default"

    def test_returns_default_when_slot_missing(self):
        """Test returns default when slot_name not found."""
        slots = {"flow1": {"slot": "value"}}
        assert get_slot_value(slots, "flow1", "other", "default") == "default"


class TestSetSlotValue:
    """Tests for set_slot_value function."""

    def test_sets_value_in_existing_flow(self):
        """Test setting slot in existing flow."""
        slots = {"flow1": {"existing": "value"}}
        result = set_slot_value(slots, "flow1", "new_slot", "new_value")
        assert result["flow1"]["new_slot"] == "new_value"
        assert result["flow1"]["existing"] == "value"

    def test_creates_flow_if_not_exists(self):
        """Test creates flow_id if not present."""
        result = set_slot_value({}, "flow1", "slot", "value")
        assert result == {"flow1": {"slot": "value"}}

    def test_does_not_mutate_original(self):
        """Test original dict is not mutated."""
        original = {"flow1": {"slot": "old"}}
        set_slot_value(original, "flow1", "slot", "new")
        assert original["flow1"]["slot"] == "old"
