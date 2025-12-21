"""Unit tests for error scenarios in node factories."""

import pytest
from pydantic import ValidationError
from soni.compiler.nodes.branch import BranchNodeFactory

from soni.config import (
    ActionStepConfig,
    BranchStepConfig,
    CollectStepConfig,
    ConfirmStepConfig,
    SayStepConfig,
    WhileStepConfig,
)
from soni.core.errors import ValidationError as SoniValidationError


class TestActionNodeFactoryErrors:
    """Error tests for ActionNodeFactory."""

    def test_missing_call_raises_error(self):
        """Should raise ValidationError when 'call' is missing."""
        # Pydantic validation
        with pytest.raises(ValidationError, match="call"):
            ActionStepConfig(step="bad_action", type="action")


class TestBranchNodeFactoryErrors:
    """Error tests for BranchNodeFactory."""

    def test_missing_slot_or_evaluate_raises_error(self):
        """Should raise ValueError when neither 'slot' nor 'evaluate' is provided."""
        # This is a logical validation in the Factory, not Pydantic
        # because slot and evaluate are optional in schema but logic requires XOR
        step = BranchStepConfig(
            step="bad_branch",
            type="branch",
            cases={"a": "node_a"},
        )
        factory = BranchNodeFactory()

        with pytest.raises(SoniValidationError, match="must specify either 'slot' or 'evaluate'"):
            factory.create(step)

    def test_missing_cases_raises_error(self):
        """Should raise ValidationError when 'cases' is missing."""
        # Pydantic validation
        with pytest.raises(ValidationError, match="cases"):
            BranchStepConfig(
                step="bad_branch",
                type="branch",
                slot="some_slot",
            )


class TestCollectNodeFactoryErrors:
    """Error tests for CollectNodeFactory."""

    def test_missing_slot_raises_error(self):
        """Should raise ValidationError when 'slot' is missing."""
        with pytest.raises(ValidationError, match="slot"):
            CollectStepConfig(step="bad_collect", type="collect")


class TestConfirmNodeFactoryErrors:
    """Error tests for ConfirmNodeFactory."""

    def test_missing_slot_raises_error(self):
        """Should raise ValidationError when 'slot' is missing."""
        with pytest.raises(ValidationError, match="slot"):
            ConfirmStepConfig(step="bad_confirm", type="confirm")


class TestSayNodeFactoryErrors:
    """Error tests for SayNodeFactory."""

    def test_missing_message_raises_error(self):
        """Should raise ValidationError when 'message' is missing."""
        with pytest.raises(ValidationError, match="message"):
            SayStepConfig(step="bad_say", type="say")


class TestWhileNodeFactoryErrors:
    """Error tests for WhileNodeFactory."""

    def test_missing_condition_raises_error(self):
        """Should raise ValidationError when 'condition' is missing."""
        with pytest.raises(ValidationError, match="condition"):
            WhileStepConfig(
                step="bad_while",
                type="while",
                do=["step1"],
            )

    def test_missing_do_raises_error(self):
        """Should raise ValidationError when 'do' is missing."""
        with pytest.raises(ValidationError, match="do"):
            WhileStepConfig(
                step="bad_while",
                type="while",
                condition="x == 1",
            )
