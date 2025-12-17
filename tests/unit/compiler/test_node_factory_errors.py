"""Unit tests for error scenarios in node factories."""

import pytest

from soni.compiler.nodes.action import ActionNodeFactory
from soni.compiler.nodes.branch import BranchNodeFactory
from soni.compiler.nodes.collect import CollectNodeFactory
from soni.compiler.nodes.confirm import ConfirmNodeFactory
from soni.compiler.nodes.say import SayNodeFactory
from soni.compiler.nodes.while_loop import WhileNodeFactory
from soni.core.config import StepConfig


class TestActionNodeFactoryErrors:
    """Error tests for ActionNodeFactory."""

    def test_missing_call_raises_error(self):
        """Should raise ValueError when 'call' is missing."""
        step = StepConfig(step="bad_action", type="action")
        factory = ActionNodeFactory()

        with pytest.raises(ValueError, match="missing required field 'call'"):
            factory.create(step)


class TestBranchNodeFactoryErrors:
    """Error tests for BranchNodeFactory."""

    def test_missing_slot_or_evaluate_raises_error(self):
        """Should raise ValueError when neither 'slot' nor 'evaluate' is provided."""
        step = StepConfig(
            step="bad_branch",
            type="branch",
            cases={"a": "node_a"},
        )
        factory = BranchNodeFactory()

        with pytest.raises(ValueError, match="must specify either 'slot' or 'evaluate'"):
            factory.create(step)

    def test_missing_cases_raises_error(self):
        """Should raise ValueError when 'cases' is missing."""
        step = StepConfig(
            step="bad_branch",
            type="branch",
            slot="some_slot",
        )
        factory = BranchNodeFactory()

        with pytest.raises(ValueError, match="missing required field 'cases'"):
            factory.create(step)


class TestCollectNodeFactoryErrors:
    """Error tests for CollectNodeFactory."""

    def test_missing_slot_raises_error(self):
        """Should raise ValueError when 'slot' is missing."""
        step = StepConfig(step="bad_collect", type="collect")
        factory = CollectNodeFactory()

        with pytest.raises(ValueError, match="missing required field 'slot'"):
            factory.create(step)


class TestConfirmNodeFactoryErrors:
    """Error tests for ConfirmNodeFactory."""

    def test_missing_slot_raises_error(self):
        """Should raise ValueError when 'slot' is missing."""
        step = StepConfig(step="bad_confirm", type="confirm")
        factory = ConfirmNodeFactory()

        with pytest.raises(ValueError, match="missing required field 'slot'"):
            factory.create(step)


class TestSayNodeFactoryErrors:
    """Error tests for SayNodeFactory."""

    def test_missing_message_raises_error(self):
        """Should raise ValueError when 'message' is missing."""
        step = StepConfig(step="bad_say", type="say")
        factory = SayNodeFactory()

        with pytest.raises(ValueError, match="missing required field 'message'"):
            factory.create(step)


class TestWhileNodeFactoryErrors:
    """Error tests for WhileNodeFactory."""

    def test_missing_condition_raises_error(self):
        """Should raise ValueError when 'condition' is missing."""
        step = StepConfig(
            step="bad_while",
            type="while",
            do=["step1"],
        )
        factory = WhileNodeFactory()

        with pytest.raises(ValueError, match="missing required field 'condition'"):
            factory.create(step)

    def test_missing_do_raises_error(self):
        """Should raise ValueError when 'do' is missing."""
        step = StepConfig(
            step="bad_while",
            type="while",
            condition="x == 1",
        )
        factory = WhileNodeFactory()

        with pytest.raises(ValueError, match="missing required field 'do'"):
            factory.create(step)
