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


class TestParentFlowStateRestoration:
    """Tests for parent flow state restoration after interruption completes."""

    def test_restore_waiting_for_slot_state(self):
        """When parent flow was collecting a slot, restore waiting_for_slot state."""
        state = {
            "flow_stack": [
                {
                    "flow_id": "parent_flow",
                    "flow_name": "transfer_funds",
                    "flow_state": "paused",
                    "current_step": "collect_amount",
                },
                {
                    "flow_id": "child_flow",
                    "flow_name": "check_balance",
                    "flow_state": "completed",
                },
            ],
            "metadata": {},
        }

        result = FlowCleanupManager.cleanup_completed_flow(state)

        # Child flow should be popped
        assert len(result["flow_stack"]) == 1
        assert result["flow_stack"][0]["flow_id"] == "parent_flow"

        # Parent state should be restored
        assert result["conversation_state"] == "waiting_for_slot"
        assert result["waiting_for_slot"] == "amount"
        assert result["current_prompted_slot"] == "amount"

    def test_restore_confirming_state(self):
        """When parent flow was confirming, restore confirming state."""
        state = {
            "flow_stack": [
                {
                    "flow_id": "parent_flow",
                    "flow_name": "transfer_funds",
                    "flow_state": "paused",
                    "current_step": "confirm_transfer",
                },
                {
                    "flow_id": "child_flow",
                    "flow_name": "check_balance",
                    "flow_state": "completed",
                },
            ],
            "metadata": {},
        }

        result = FlowCleanupManager.cleanup_completed_flow(state)

        assert result["conversation_state"] == "confirming"
        assert "waiting_for_slot" not in result or result.get("waiting_for_slot") is None

    def test_restore_idle_for_unknown_step_type(self):
        """When parent step type is unknown, default to idle."""
        state = {
            "flow_stack": [
                {
                    "flow_id": "parent_flow",
                    "flow_name": "transfer_funds",
                    "flow_state": "paused",
                    "current_step": "execute_transfer",  # action step, not collect
                },
                {
                    "flow_id": "child_flow",
                    "flow_name": "check_balance",
                    "flow_state": "completed",
                },
            ],
            "metadata": {},
        }

        result = FlowCleanupManager.cleanup_completed_flow(state)

        assert result["conversation_state"] == "idle"

    def test_no_parent_flow_no_state_restoration(self):
        """When no parent flow exists, no conversation_state in result."""
        state = {
            "flow_stack": [
                {
                    "flow_id": "only_flow",
                    "flow_name": "check_balance",
                    "flow_state": "completed",
                },
            ],
            "metadata": {},
        }

        result = FlowCleanupManager.cleanup_completed_flow(state)

        # Stack should be empty
        assert result["flow_stack"] == []
        # No conversation_state should be set (handled elsewhere)
        assert "conversation_state" not in result

    def test_parent_with_no_current_step(self):
        """When parent has no current_step, default to idle."""
        state = {
            "flow_stack": [
                {
                    "flow_id": "parent_flow",
                    "flow_name": "transfer_funds",
                    "flow_state": "paused",
                    "current_step": None,
                },
                {
                    "flow_id": "child_flow",
                    "flow_name": "check_balance",
                    "flow_state": "completed",
                },
            ],
            "metadata": {},
        }

        result = FlowCleanupManager.cleanup_completed_flow(state)

        assert result["conversation_state"] == "idle"
