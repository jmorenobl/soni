"""Dataset builder - combines patterns, domains, and contexts."""

from typing import Literal

import dspy
from soni.dataset.base import DomainConfig, PatternGenerator
from soni.dataset.domains import ALL_DOMAINS
from soni.dataset.edge_cases import get_all_edge_cases
from soni.dataset.patterns import ALL_PATTERN_GENERATORS


class DatasetBuilder:
    """Builds training datasets by combining patterns, domains, and contexts.

    This class orchestrates the generation of examples by combining:
    - Patterns: 9 conversational patterns (SLOT_VALUE, CORRECTION, etc.)
    - Domains: 4+ business domains (flight_booking, hotel_booking, etc.)
    - Contexts: 2 context types (cold_start, ongoing)

    Example:
        builder = DatasetBuilder()
        trainset = builder.build(
            patterns=["slot_value", "correction"],
            domains=["flight_booking", "hotel_booking"],
            contexts=["ongoing"],
            examples_per_combination=2,
        )
        # Result: 2 patterns × 2 domains × 1 context × 2 examples = 8 examples
    """

    def __init__(
        self,
        pattern_generators: dict[str, PatternGenerator] | None = None,
        domain_configs: dict[str, DomainConfig] | None = None,
    ):
        """Initialize builder with registries.

        Args:
            pattern_generators: Registry of pattern generators (default: auto-discover)
            domain_configs: Registry of domain configs (default: auto-discover)
        """
        # Auto-discover if not provided
        self.pattern_generators = pattern_generators or ALL_PATTERN_GENERATORS.copy()
        self.domain_configs = domain_configs or ALL_DOMAINS.copy()

    def register_pattern(self, name: str, generator: PatternGenerator) -> None:
        """Register a pattern generator.

        Args:
            name: Pattern identifier (e.g., "slot_value")
            generator: Pattern generator instance
        """
        self.pattern_generators[name] = generator

    def register_domain(self, config: DomainConfig) -> None:
        """Register a domain configuration.

        Args:
            config: Domain configuration
        """
        self.domain_configs[config.name] = config

    def build(
        self,
        patterns: list[str] | None = None,
        domains: list[str] | None = None,
        contexts: list[Literal["cold_start", "ongoing"]] | None = None,
        examples_per_combination: int = 2,
    ) -> list[dspy.Example]:
        """Build dataset from specified dimensions.

        Args:
            patterns: List of pattern names (default: all registered)
            domains: List of domain names (default: all registered)
            contexts: List of context types (default: both)
            examples_per_combination: Examples per (pattern × domain × context)

        Returns:
            List of dspy.Example ready for optimization

        Raises:
            ValueError: If requested pattern/domain not registered
        """
        patterns = patterns or list(self.pattern_generators.keys())
        domains = domains or list(self.domain_configs.keys())
        contexts = contexts or ["cold_start", "ongoing"]

        # Validate all requested patterns and domains are registered
        for pattern in patterns:
            if pattern not in self.pattern_generators:
                raise ValueError(f"Pattern '{pattern}' not registered")

        for domain in domains:
            if domain not in self.domain_configs:
                raise ValueError(f"Domain '{domain}' not registered")

        all_examples: list[dspy.Example] = []

        # Generate all combinations
        for pattern_name in patterns:
            for domain_name in domains:
                for context_type in contexts:
                    generator = self.pattern_generators[pattern_name]
                    domain_config = self.domain_configs[domain_name]

                    # Generate templates
                    templates = generator.generate_examples(
                        domain_config=domain_config,
                        context_type=context_type,
                        count=examples_per_combination,
                    )

                    # Convert to dspy.Example
                    examples = [template.to_dspy_example(domain_config) for template in templates]

                    all_examples.extend(examples)

        return all_examples

    def build_all(
        self,
        examples_per_combination: int = 2,
        include_edge_cases: bool = True,
    ) -> list[dspy.Example]:
        """Build complete dataset with all registered patterns, domains, and contexts.

        Args:
            examples_per_combination: Examples per (pattern × domain × context)
            include_edge_cases: Whether to include boundary examples for robustness

        Returns:
            Complete training dataset including edge cases
        """
        examples = self.build(
            patterns=None,
            domains=None,
            contexts=None,
            examples_per_combination=examples_per_combination,
        )

        # Add edge cases for boundary robustness
        if include_edge_cases:
            edge_case_templates = get_all_edge_cases()
            for template in edge_case_templates:
                domain_config = self.domain_configs.get(template.domain)
                if domain_config:
                    examples.append(template.to_dspy_example(domain_config))

        return examples

    def get_stats(self) -> dict[str, int]:
        """Get statistics about registered generators and domains.

        Returns:
            Dictionary with counts of patterns, domains, and estimated examples
        """
        num_patterns = len(self.pattern_generators)
        num_domains = len(self.domain_configs)
        num_contexts = 2  # cold_start, ongoing

        return {
            "patterns": num_patterns,
            "domains": num_domains,
            "contexts": num_contexts,
            "max_combinations": num_patterns * num_domains * num_contexts,
        }
