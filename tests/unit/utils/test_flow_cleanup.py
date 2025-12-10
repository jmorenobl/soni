"""Tests for FlowCleanupManager utility."""

import pytest

from soni.utils.flow_cleanup import FlowCleanupManager


def test_cleanup_completed_flow():
    """Test cleanup removes completed flow from stack."""
    state = {
        "flow_stack": [{"flow_id": "flow1", "flow_state": "completed"}],
        "metadata": {},
    }

    result = FlowCleanupManager.cleanup_completed_flow(state)

    assert result["flow_stack"] == []
    assert len(result["metadata"]["completed_flows"]) == 1
    assert result["metadata"]["completed_flows"][0]["flow_id"] == "flow1"


def test_no_cleanup_when_not_completed():
    """Test no cleanup when flow not completed."""
    state = {
        "flow_stack": [{"flow_id": "flow1", "flow_state": "active"}],
        "metadata": {},
    }

    result = FlowCleanupManager.cleanup_completed_flow(state)

    assert result == {}


def test_no_cleanup_when_stack_empty():
    """Test no cleanup when flow stack is empty."""
    state = {
        "flow_stack": [],
        "metadata": {},
    }

    result = FlowCleanupManager.cleanup_completed_flow(state)

    assert result == {}


def test_should_cleanup_returns_true():
    """Test should_cleanup returns True for completed flow."""
    state = {
        "flow_stack": [{"flow_id": "flow1", "flow_state": "completed"}],
    }

    result = FlowCleanupManager.should_cleanup(state)

    assert result is True


def test_should_cleanup_returns_false():
    """Test should_cleanup returns False for active flow."""
    state = {
        "flow_stack": [{"flow_id": "flow1", "flow_state": "active"}],
    }

    result = FlowCleanupManager.should_cleanup(state)

    assert result is False


def test_should_cleanup_empty_stack():
    """Test should_cleanup returns False when stack is empty."""
    state = {"flow_stack": []}

    result = FlowCleanupManager.should_cleanup(state)

    assert result is False
