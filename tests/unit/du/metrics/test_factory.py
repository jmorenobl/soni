from unittest.mock import MagicMock

import pytest

from soni.core.commands import StartFlow
from soni.du.metrics.factory import create_granular_metric, create_strict_metric
from soni.du.models import NLUOutput


class TestMetricFactory:
    """Tests for metric factory functions."""

    def test_granular_metric(self):
        """Should yield float scores."""
        metric_fn = create_granular_metric()

        example = MagicMock()
        example.result = NLUOutput(commands=[StartFlow(flow_name="test")])

        # Perfect
        pred = NLUOutput(commands=[StartFlow(flow_name="test")])
        assert metric_fn(example, pred) == 1.0

        # Partial
        pred_partial = NLUOutput(commands=[StartFlow(flow_name="other")])
        assert 0 < metric_fn(example, pred_partial) < 1.0

        # None
        assert metric_fn(example, NLUOutput(commands=[])) == 0.0

    def test_strict_metric(self):
        """Should yield boolean results."""
        metric_fn = create_strict_metric()

        example = MagicMock()
        example.result = NLUOutput(commands=[StartFlow(flow_name="test")])

        # Perfect -> True
        pred = NLUOutput(commands=[StartFlow(flow_name="test")])
        assert metric_fn(example, pred) is True

        # Partial -> False
        pred_partial = NLUOutput(commands=[StartFlow(flow_name="other")])
        assert metric_fn(example, pred_partial) is False

    def test_factory_error_handling(self):
        """Should handle missing result in example."""
        metric_fn = create_granular_metric()
        example = MagicMock()
        example.result = None
        assert metric_fn(example, MagicMock()) == 0.0

    def test_granular_metric_wrappers(self):
        """Should handle different prediction formats."""
        metric_fn = create_granular_metric()
        example = MagicMock()
        example.result = NLUOutput(commands=[StartFlow(flow_name="t")])

        # Wrapped in Prediction
        pred_wrapped = MagicMock()
        pred_wrapped.result = NLUOutput(commands=[StartFlow(flow_name="t")])
        assert metric_fn(example, pred_wrapped) == 1.0

        # Direct with commands
        class Simple:
            commands = [StartFlow(flow_name="t")]

        assert metric_fn(example, Simple()) == 1.0

        # Unsupported
        assert metric_fn(example, "wrong") == 0.0

    def test_factory_exception_handling(self):
        """Should catch AttributeErrors."""
        metric_fn = create_granular_metric()
        example = MagicMock()
        example.result = 123  # Will fail .commands
        assert metric_fn(example, NLUOutput(commands=[])) == 0.0
