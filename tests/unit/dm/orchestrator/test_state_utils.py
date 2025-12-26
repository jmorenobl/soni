"""Tests for orchestrator state utilities."""

from typing import Any, cast

import pytest

from soni.core.types import DialogueState
from soni.dm.orchestrator.state_utils import (
    build_merged_return,
    build_subgraph_state,
    merge_outputs,
    merge_state,
    transform_result,
)


class TestMergeState:
    """Tests for merge_state function."""

    def test_merge_state_overwrites_existing_keys(self):
        """Test that delta values override base values."""
        base = cast(DialogueState, {"a": 1, "b": 2})
        delta = {"b": 3}
        result = merge_state(base, delta)
        assert result.get("a") == 1
        assert result.get("b") == 3

    def test_merge_state_adds_new_keys(self):
        """Test that new keys from delta are added."""
        base = cast(DialogueState, {"a": 1})
        delta = {"b": 2}
        result = merge_state(base, delta)
        assert result.get("a") == 1
        assert result.get("b") == 2

    def test_merge_state_does_not_mutate_inputs(self):
        """Test that input dicts are not modified."""
        base = cast(DialogueState, {"a": 1})
        delta = {"b": 2}
        merge_state(base, delta)
        assert base.get("a") == 1
        assert delta == {"b": 2}

    def test_merge_state_handles_executed_steps(self):
        """Test additive merge for _executed_steps."""
        base = cast(DialogueState, {"_executed_steps": {"flow1": {1, 2}}})
        delta = {"_executed_steps": {"flow1": {3}, "flow2": {1}}}
        result = merge_state(base, delta)
        steps = result.get("_executed_steps")
        assert steps is not None
        assert steps["flow1"] == {1, 2, 3}
        assert steps["flow2"] == {1}


class TestBuildSubgraphState:
    """Tests for build_subgraph_state function."""

    def test_extracts_required_fields(self):
        """Test that required fields are extracted."""
        state = cast(
            DialogueState,
            {
                "messages": [{"role": "user", "content": "hi"}],
                "flow_stack": [{"flow_id": "test"}],
                "flow_slots": {"test": {"slot": "value"}},
                "extra_field": "ignored",
                "user_message": "hi",
                "commands": [],
                "_executed_steps": {},
            },
        )
        result = build_subgraph_state(state)
        assert "messages" in result
        assert "flow_stack" in result
        assert "flow_slots" in result
        assert "user_message" in result
        assert "commands" in result
        assert "_executed_steps" in result
        assert "extra_field" not in result

    def test_handles_missing_fields_with_defaults(self):
        """Test that missing fields get defaults."""
        result = build_subgraph_state(cast(DialogueState, {}))
        assert result["messages"] == []
        assert result["flow_stack"] == []
        assert result["flow_slots"] == {}
        assert result["user_message"] is None


class TestMergeOutputs:
    """Tests for merge_outputs function."""

    def test_merges_simple_values(self):
        """Test merging simple key-value pairs."""
        target = {"a": 1}
        source = {"b": 2}
        merge_outputs(target, source)
        assert target == {"a": 1, "b": 2}

    def test_deep_merges_flow_slots(self):
        """Test that flow_slots are deep merged."""
        target = {"flow_slots": {"flow1": {"slot1": "a"}}}
        source = {"flow_slots": {"flow1": {"slot2": "b"}}}
        merge_outputs(target, source)
        assert target["flow_slots"]["flow1"] == {"slot1": "a", "slot2": "b"}


class TestBuildMergedReturn:
    """Tests for build_merged_return function."""

    def test_combines_updates_and_output(self):
        """Test combining updates with final output."""
        updates = cast(DialogueState, {"key1": "value1"})
        final_output = {"key2": "value2"}
        result = build_merged_return(updates, final_output, None)
        assert result.get("key1") == "value1"
        assert result.get("key2") == "value2"

    def test_includes_pending_task_when_present(self):
        """Test pending task is included when not None."""
        pending = {"task": "data"}
        result = build_merged_return(cast(DialogueState, {}), {}, pending)
        assert result["_pending_task"] == pending
