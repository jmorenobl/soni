"""Integration tests for complete dataset generation."""

import dspy
import pytest

from soni.dataset.builder import DatasetBuilder


class TestDatasetGenerationIntegration:
    """Integration tests for DatasetBuilder with multiple generators."""

    def test_complex_dataset_build(self):
        """Should build a varied dataset using different patterns and domains."""
        builder = DatasetBuilder()

        dataset = builder.build(
            patterns=["cancellation", "correction", "digression"],
            domains=["banking"],
            contexts=["ongoing"],
            examples_per_combination=1,
        )

        assert len(dataset) == 3
        assert all(isinstance(ex, dspy.Example) for ex in dataset)

        # Verify variety of commands (approximate as it depends on generator logic)
        command_names = set()
        for ex in dataset:
            if hasattr(ex, "result") and hasattr(ex.result, "commands"):
                for cmd in ex.result.commands:
                    command_names.add(cmd.__class__.__name__)

        assert len(command_names) > 0

    def test_dataset_uniqueness(self):
        """Generated dataset should have a reasonable level of uniqueness."""
        builder = DatasetBuilder()
        dataset = builder.build(
            patterns=["cancellation"],
            domains=["banking"],
            contexts=["ongoing"],
            examples_per_combination=10,
        )

        messages = [ex.user_message for ex in dataset]
        unique_messages = set(messages)

        # Variety should be > 50%
        assert len(unique_messages) / len(messages) >= 0.5
