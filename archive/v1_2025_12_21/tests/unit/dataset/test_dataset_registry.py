"""Tests for dataset registry utilities."""

import dspy
import pytest

from soni.dataset.builder import DatasetBuilder
from soni.dataset.registry import print_dataset_stats, validate_dataset


class TestValidateDataset:
    """Tests for validate_dataset function."""

    def test_empty_dataset_raises(self):
        """Test that empty dataset raises ValueError."""
        with pytest.raises(ValueError, match="Dataset is empty"):
            validate_dataset([])

    def test_valid_dataset_returns_stats(self):
        """Test that valid dataset returns statistics."""
        builder = DatasetBuilder()
        examples = builder.build(
            patterns=["slot_value"],
            domains=["flight_booking"],
            contexts=["ongoing"],
            examples_per_combination=2,
        )
        stats = validate_dataset(examples)

        assert "total_examples" in stats
        assert "commands" in stats
        assert "validation_errors" in stats
        assert stats["total_examples"] >= 1

    def test_counts_commands(self):
        """Test that commands are counted correctly."""
        builder = DatasetBuilder()
        examples = builder.build(
            patterns=["slot_value"],
            domains=["flight_booking"],
            contexts=["ongoing"],
            examples_per_combination=2,
        )
        stats = validate_dataset(examples)

        # Should have some command counts
        assert isinstance(stats["commands"], dict)


class TestPrintDatasetStats:
    """Tests for print_dataset_stats function."""

    def test_prints_empty_message_for_empty(self, capsys):
        """Test empty dataset message."""
        print_dataset_stats([])
        captured = capsys.readouterr()
        assert "empty" in captured.out.lower()

    def test_prints_stats_for_valid_dataset(self, capsys):
        """Test that stats are printed for valid dataset."""
        builder = DatasetBuilder()
        examples = builder.build(
            patterns=["slot_value"],
            domains=["flight_booking"],
            contexts=["ongoing"],
            examples_per_combination=2,
        )
        print_dataset_stats(examples)
        captured = capsys.readouterr()

        assert "Dataset Statistics" in captured.out
        assert "Total examples" in captured.out
