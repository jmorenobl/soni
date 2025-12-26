"""Tests for core dataset builder."""

import dspy
import pytest

from soni.dataset.builder import DatasetBuilder


class TestDatasetBuilder:
    """Tests for DatasetBuilder class."""

    def test_builder_initialization(self):
        """Builder should initialize with default generators and domains."""
        builder = DatasetBuilder()
        assert len(builder.pattern_generators) > 0
        assert len(builder.domain_configs) > 0

    def test_register_pattern(self):
        """Should register pattern generator."""
        from unittest.mock import MagicMock

        from soni.dataset.base import PatternGenerator

        builder = DatasetBuilder()
        generator = MagicMock(spec=PatternGenerator)
        builder.register_pattern("new_pattern", generator)
        assert "new_pattern" in builder.pattern_generators

    def test_build_dataset(self):
        """Should generate examples using build()."""
        builder = DatasetBuilder()
        # Using banking domain which is auto-discovered
        # We need a pattern that supports the domain
        dataset = builder.build(
            patterns=["cancellation"],
            domains=["banking"],
            contexts=["ongoing"],
            examples_per_combination=1,
        )
        assert len(dataset) == 1
        assert isinstance(dataset[0], dspy.Example)

    def test_build_all(self):
        """Should build complete dataset."""
        builder = DatasetBuilder()
        dataset = builder.build_all(examples_per_combination=1, include_edge_cases=False)
        # 9 patterns * 5 domains * 2 contexts = 90 examples (at least)
        # Some combinations might return empty lists (e.g. cold_start for correction)
        # So we just check that it's non-empty and reasonably large
        assert len(dataset) > 30
