from unittest.mock import MagicMock, patch

import pytest

from soni.dataset.builder import DatasetBuilder
from soni.du.models import NLUOutput
from soni.du.optimizer import create_metric, optimize_du


class TestOptimizationIntegration:
    """Integration-like tests for optimization workflow."""

    @pytest.mark.asyncio
    async def test_optimize_du_workflow_with_builder(self):
        """Should simulate a full optimization cycle with DatasetBuilder."""
        # 1. Build a small dataset
        builder = DatasetBuilder()
        builder.add_pattern("cancellation", flow_name="transfer", num_examples=2)
        dataset = builder.build()

        # Convert to Examples (DSPy format)
        examples = [ex.to_dspy_example() for ex in dataset]

        # 2. Setup metric
        metric = create_metric()

        # 3. Optimize with mocks
        with patch("soni.du.optimizer.MIPROv2") as mock_miprov2:
            mock_optimized = MagicMock()
            mock_miprov2.return_value.compile.return_value = mock_optimized

            optimized_program = optimize_du(
                trainset=examples, metric=metric, optimizer_type="miprov2", auto="light"
            )

            # 4. Verify
            assert optimized_program == mock_optimized
            mock_miprov2.return_value.compile.assert_called_once()

            # Check a few kwargs in compile call
            call_args = mock_miprov2.return_value.compile.call_args
            assert call_args.kwargs["trainset"] == examples

    @pytest.mark.asyncio
    async def test_slot_extractor_optimization_workflow(self):
        """Should simulate slot extractor optimization."""
        from soni.du.metrics.adapters import create_slot_extraction_metric
        from soni.du.optimizer import optimize_slot_extractor

        # Small dataset
        examples = [MagicMock() for _ in range(2)]
        metric = create_slot_extraction_metric()

        with patch("soni.du.optimizer.MIPROv2") as mock_miprov2:
            mock_optimized = MagicMock()
            mock_miprov2.return_value.compile.return_value = mock_optimized

            result = optimize_slot_extractor(examples, metric)

            assert result == mock_optimized
            mock_miprov2.return_value.compile.assert_called_once()
