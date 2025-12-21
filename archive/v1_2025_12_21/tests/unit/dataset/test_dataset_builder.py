"""Tests for DatasetBuilder."""

import dspy
import pytest
from soni.dataset.base import DomainConfig, DomainExampleData, PatternGenerator
from soni.dataset.builder import DatasetBuilder
from soni.dataset.domains import ALL_DOMAINS


class TestDatasetBuilder:
    """Tests for DatasetBuilder class."""

    def test_default_initialization(self):
        """Test builder initializes with all patterns and domains."""
        builder = DatasetBuilder()
        stats = builder.get_stats()
        assert stats["patterns"] == 8  # All 8 pattern generators
        assert stats["domains"] == 5  # All 5 domains
        assert stats["contexts"] == 2

    def test_custom_single_patterns(self):
        """Test builder with subset of patterns."""
        from soni.dataset.patterns.slot_value import SlotValueGenerator

        builder = DatasetBuilder(
            pattern_generators={"slot_value": SlotValueGenerator()},
            domain_configs=ALL_DOMAINS,
        )
        stats = builder.get_stats()
        assert stats["patterns"] == 1
        assert stats["domains"] == 5

    def test_register_pattern(self):
        """Test registering a new pattern generator."""
        builder = DatasetBuilder(pattern_generators={}, domain_configs={})

        class FakeGenerator(PatternGenerator):
            def generate_examples(self, domain_config, context_type, count=3):
                return []

        builder.register_pattern("fake", FakeGenerator())
        assert "fake" in builder.pattern_generators

    def test_register_domain(self):
        """Test registering a new domain configuration."""
        builder = DatasetBuilder(pattern_generators={}, domain_configs={})

        domain = DomainConfig(
            name="test_domain",
            description="Test",
            available_flows=["test_flow"],
            flow_descriptions={"test_flow": "Test flow"},
            available_actions=[],
            slots={"slot1": "string"},
            slot_prompts={"slot1": "What?"},
            example_data=DomainExampleData(
                slot_values={"slot1": ["val1"]},
                trigger_intents={"test_flow": ["test"]},
            ),
        )

        builder.register_domain(domain)
        assert "test_domain" in builder.domain_configs

    def test_build_single_combination(self):
        """Test building dataset with single combination."""
        builder = DatasetBuilder()
        examples = builder.build(
            patterns=["slot_value"],
            domains=["flight_booking"],
            contexts=["ongoing"],
            examples_per_combination=2,
        )
        assert len(examples) >= 1
        assert all(isinstance(ex, dspy.Example) for ex in examples)

    def test_build_multiple_patterns(self):
        """Test building with multiple patterns."""
        builder = DatasetBuilder()
        examples = builder.build(
            patterns=["slot_value", "correction"],
            domains=["flight_booking"],
            contexts=["ongoing"],
            examples_per_combination=1,
        )
        # Should have at least 1 from each pattern
        assert len(examples) >= 2

    def test_build_multiple_domains(self):
        """Test building with multiple domains."""
        builder = DatasetBuilder()
        examples = builder.build(
            patterns=["slot_value"],
            domains=["flight_booking", "banking"],
            contexts=["ongoing"],
            examples_per_combination=1,
        )
        # Should have at least 1 from each domain
        assert len(examples) >= 2

    def test_build_invalid_pattern_raises(self):
        """Test that invalid pattern raises ValueError."""
        builder = DatasetBuilder()
        with pytest.raises(ValueError, match="Pattern 'nonexistent' not registered"):
            builder.build(patterns=["nonexistent"])

    def test_build_invalid_domain_raises(self):
        """Test that invalid domain raises ValueError."""
        builder = DatasetBuilder()
        with pytest.raises(ValueError, match="Domain 'nonexistent' not registered"):
            builder.build(domains=["nonexistent"])

    def test_build_all(self):
        """Test building complete dataset."""
        builder = DatasetBuilder()
        examples = builder.build_all(examples_per_combination=1, include_edge_cases=False)
        # Should have many examples
        assert len(examples) > 0
        assert all(isinstance(ex, dspy.Example) for ex in examples)

    def test_build_all_with_edge_cases(self):
        """Test building with edge cases included."""
        builder = DatasetBuilder()
        without_edge = builder.build_all(examples_per_combination=1, include_edge_cases=False)
        with_edge = builder.build_all(examples_per_combination=1, include_edge_cases=True)
        # With edge cases should potentially have more (or same if no edge cases defined)
        assert len(with_edge) >= len(without_edge)

    def test_get_stats(self):
        """Test get_stats returns correct structure."""
        builder = DatasetBuilder()
        stats = builder.get_stats()
        assert "patterns" in stats
        assert "domains" in stats
        assert "contexts" in stats
        assert "max_combinations" in stats
        assert stats["max_combinations"] == stats["patterns"] * stats["domains"] * stats["contexts"]
