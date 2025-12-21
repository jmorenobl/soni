"""Public API for dataset creation.

This module provides the infrastructure for creating training datasets
for DSPy NLU optimization. It combines conversational patterns, business
domains, and conversation contexts to generate comprehensive examples.

Usage:
    from soni.dataset import DatasetBuilder

    builder = DatasetBuilder()
    trainset = builder.build_all(examples_per_combination=2)
"""

from soni.dataset.base import (
    ConversationContext,
    DomainConfig,
    DomainExampleData,
    ExampleTemplate,
    PatternGenerator,
)
from soni.dataset.builder import DatasetBuilder
from soni.dataset.edge_cases import get_all_edge_cases
from soni.dataset.registry import print_dataset_stats, validate_dataset

__all__ = [
    "DatasetBuilder",
    "DomainConfig",
    "DomainExampleData",
    "ConversationContext",
    "ExampleTemplate",
    "PatternGenerator",
    "get_all_edge_cases",
    "validate_dataset",
    "print_dataset_stats",
]
