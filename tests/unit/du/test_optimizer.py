from typing import cast
from unittest.mock import MagicMock, patch

import dspy
import pytest

from soni.core.commands import SetSlot, StartFlow
from soni.du.models import NLUOutput
from soni.du.optimizer import (
    create_metric,
    default_command_validator,
    optimize_du,
    optimize_slot_extractor,
)


class TestOptimizerLogic:
    """Tests for optimizer.py logic and metrics."""

    def test_default_command_validator(self):
        """Should compare commands by type and key fields."""
        cmd1 = StartFlow(flow_name="test", slots={"a": 1})
        cmd2 = StartFlow(flow_name="test", slots={"a": 1})
        cmd3 = StartFlow(flow_name="other")
        cmd4 = SetSlot(slot="s", value="v")

        assert default_command_validator(cmd1, cmd2) is True
        assert default_command_validator(cmd1, cmd3) is False
        assert default_command_validator(cmd1, cmd4) is False

    def test_create_metric_success(self):
        """Should create a metric that compares NLUOutput lists."""
        metric_fn = create_metric()

        example = MagicMock()
        example.result = NLUOutput(commands=[StartFlow(flow_name="test")], confidence=1.0)

        # Exact match
        prediction = NLUOutput(commands=[StartFlow(flow_name="test")], confidence=0.5)
        assert metric_fn(example, prediction) is True

        # Mismatch length
        prediction_short = NLUOutput(commands=[])
        assert metric_fn(example, prediction_short) is False

        # Mismatch content
        prediction_diff = NLUOutput(commands=[StartFlow(flow_name="diff")])
        assert metric_fn(example, prediction_diff) is False

    def test_create_metric_prediction_wrappers(self):
        """Should handle various prediction formats (wrapped or direct)."""
        metric_fn = create_metric()
        example = MagicMock()
        example.result = NLUOutput(commands=[SetSlot(slot="s", value="v")])

        # Case 1: Wrapped in dspy.Prediction (has result attribute)
        pred_wrapped = MagicMock()
        pred_wrapped.result = NLUOutput(commands=[SetSlot(slot="s", value="v")])
        assert metric_fn(example, pred_wrapped) is True

        # Case 2: Direct object with commands attribute
        class SimplePred:
            def __init__(self, cmds):
                self.commands = cmds

        assert metric_fn(example, SimplePred([SetSlot(slot="s", value="v")])) is True

    def test_create_metric_error_handling(self):
        """Should return False on invalid inputs."""
        metric_fn = create_metric()
        assert metric_fn(None, None) is False

        example = MagicMock()
        example.result = None
        assert metric_fn(example, MagicMock()) is False

    @patch("soni.du.optimizer.MIPROv2")
    def test_optimize_du_miprov2(self, mock_miprov2):
        """Should configure and call MIPROv2 compiler."""
        # Setup mocks
        mock_compiled = MagicMock()
        mock_miprov2.return_value.compile.return_value = mock_compiled

        trainset = [MagicMock()]
        metric = MagicMock()

        result = optimize_du(trainset, metric, optimizer_type="miprov2")

        # Verify optimizer was created with correct settings
        mock_miprov2.assert_called_once()
        # Verify compile was called
        mock_miprov2.return_value.compile.assert_called_once()
        assert result == mock_compiled

    @patch("soni.du.optimizer.dspy.GEPA")
    @patch("soni.du.optimizer.adapt_metric_for_gepa")
    def test_optimize_du_gepa(self, mock_adapt, mock_gepa):
        """Should configure and call GEPA compiler."""
        mock_compiled = MagicMock()
        mock_gepa.return_value.compile.return_value = mock_compiled

        trainset = [MagicMock()]
        metric = MagicMock()

        result = optimize_du(trainset, metric, optimizer_type="gepa")

        mock_gepa.assert_called_once()
        mock_gepa.return_value.compile.assert_called_once()
        assert result == mock_compiled

    @patch("soni.du.optimizer.MIPROv2")
    def test_optimize_du_with_valset(self, mock_miprov2):
        """Should include valset in compile call if provided."""
        mock_compiled = MagicMock()
        mock_miprov2.return_value.compile.return_value = mock_compiled

        trainset = [MagicMock()]
        valset = [MagicMock()]
        metric = MagicMock()

        optimize_du(trainset, metric, valset=valset)

        args, kwargs = mock_miprov2.return_value.compile.call_args
        assert "valset" in kwargs
        assert kwargs["valset"] == valset

    @patch("soni.du.optimizer.dspy.GEPA")
    @patch("soni.du.optimizer.adapt_metric_for_gepa")
    def test_optimize_slot_extractor_gepa(self, mock_adapt, mock_gepa):
        """Should use GEPA for slot extraction if requested."""
        mock_compiled = MagicMock()
        mock_gepa.return_value.compile.return_value = mock_compiled

        trainset = [MagicMock()]
        metric = MagicMock()

        optimize_slot_extractor(trainset, metric, optimizer_type="gepa")

        mock_gepa.assert_called_once()
        mock_gepa.return_value.compile.assert_called_once()

    @patch("soni.du.optimizer.MIPROv2")
    def test_optimize_slot_extractor_with_valset(self, mock_miprov2):
        """Should include valset in slot extractor compile call."""
        mock_compiled = MagicMock()
        mock_miprov2.return_value.compile.return_value = mock_compiled

        trainset = [MagicMock()]
        valset = [MagicMock()]
        metric = MagicMock()

        optimize_slot_extractor(trainset, metric, valset=valset)

        args, kwargs = mock_miprov2.return_value.compile.call_args
        assert kwargs["valset"] == valset

    def test_create_metric_unsupported_format(self):
        """Should return False for unsupported prediction format."""
        metric_fn = create_metric()
        example = MagicMock()
        example.result = NLUOutput(commands=[])

        assert metric_fn(example, "not a prediction") is False

    def test_create_metric_exception_handling(self):
        """Should return False if accessing attributes raises exception."""
        metric_fn = create_metric()
        example = MagicMock()
        # Force a TypeError by making example.result something that won't work
        example.result = 123
        # This will fail at example.result.commands
        assert metric_fn(example, NLUOutput(commands=[])) is False

    @patch("soni.du.optimizer._create_miprov2_optimizer")
    def test_optimize_du_optimizer_config(self, mock_create):
        """Should pass configuration to MIPROv2 creator."""
        mock_create.return_value = MagicMock()
        trainset = [MagicMock()]
        metric = MagicMock()

        optimize_du(
            trainset, metric, optimizer_type="miprov2", max_bootstrapped_demos=10, num_threads=8
        )

        args, kwargs = mock_create.call_args
        assert kwargs["max_bootstrapped_demos"] == 10
        assert kwargs["num_threads"] == 8
