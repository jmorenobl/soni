import pytest

from soni.core.commands import CancelFlow, SetSlot, StartFlow
from soni.du.metrics.scoring import score_command_lists, score_command_pair


class TestScoring:
    """Tests for command scoring logic."""

    def test_score_command_pair_matching(self):
        """Should score identical commands as 1.0."""
        cmd_exp = StartFlow(flow_name="test")
        cmd_act = StartFlow(flow_name="test")
        score = score_command_pair(cmd_exp, cmd_act)
        assert score.total == 1.0

    def test_score_command_pair_wrong_type(self):
        """Should score different types as 0.0."""
        cmd_exp = StartFlow(flow_name="test")
        cmd_act = CancelFlow()
        score = score_command_pair(cmd_exp, cmd_act)
        assert score.total == 0.0

    def test_score_command_pair_partial_key(self):
        """Should score partial matches for key fields."""
        cmd_exp = StartFlow(flow_name="test")
        cmd_act = StartFlow(flow_name="other")
        score = score_command_pair(cmd_exp, cmd_act)
        # Type=1.0 (50%), Field=0.0 (30%), Value=1.0 (no value fields) (20%)
        # Total = 0.5 + 0.0 + 0.2 = 0.7
        assert score.type_score == 1.0
        assert score.field_score == 0.0
        assert score.total == 0.7

    def test_score_command_pair_partial_value(self):
        """Should score partial matches for value fields."""
        cmd_exp = SetSlot(slot="user", value="John Doe")
        cmd_act = SetSlot(slot="user", value="John")
        score = score_command_pair(cmd_exp, cmd_act)
        # Type=1.0 (50%), Field=1.0 (slot match) (30%), Value=0.5 (fuzzy match) (20%)
        # Total = 0.5 + 0.3 + 0.1 = 0.9
        assert score.value_score == 0.5
        assert score.total == pytest.approx(0.9)

    def test_score_command_lists_identical(self):
        """Should score identical lists as 1.0."""
        cmds = [StartFlow(flow_name="a"), CancelFlow()]
        assert score_command_lists(cmds, cmds) == 1.0

    def test_score_command_lists_empty(self):
        """Should handle empty lists."""
        assert score_command_lists([], []) == 1.0
        assert score_command_lists([StartFlow(flow_name="a")], []) == 0.0
        assert score_command_lists([], [StartFlow(flow_name="a")]) == 0.0

    def test_score_command_lists_reordered(self):
        """Should handle reordered lists using best match."""
        cmd1 = StartFlow(flow_name="a")
        cmd2 = CancelFlow()
        assert score_command_lists([cmd1, cmd2], [cmd2, cmd1]) == 1.0

    def test_score_command_lists_penalty(self):
        """Should penalize extra commands."""
        cmd1 = StartFlow(flow_name="a")
        # Extra command penalty is 0.1 per command
        score = score_command_lists([cmd1], [cmd1, cmd1])
        assert score == 0.9
