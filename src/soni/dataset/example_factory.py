"""Factory for generating varied training examples.

This module provides utilities for dynamic example generation to increase
dataset variability and improve NLU optimization quality.
"""

import random
from typing import Any


class ExampleFactory:
    """Factory for generating varied training examples dynamically.

    Provides methods for random selection of slot values, utterance templates,
    and optional noise injection to create more diverse training data.

    Attributes:
        rng: Random number generator for reproducible generation.
    """

    def __init__(self, seed: int | None = None):
        """Initialize the factory with optional seed for reproducibility.

        Args:
            seed: Random seed for deterministic generation. If None, uses
                  system randomness.
        """
        self.rng = random.Random(seed)

    def choice(self, items: list[Any]) -> Any:
        """Select a random item from a list.

        Args:
            items: List of items to choose from.

        Returns:
            A randomly selected item.

        Raises:
            ValueError: If items list is empty.
        """
        if not items:
            raise ValueError("Cannot choose from empty list")
        return self.rng.choice(items)

    def sample(self, items: list[Any], k: int) -> list[Any]:
        """Sample k items from a list without replacement.

        Args:
            items: List of items to sample from.
            k: Number of items to sample.

        Returns:
            List of k randomly selected items.
        """
        k = min(k, len(items))
        return self.rng.sample(items, k)

    def shuffle(self, items: list[Any]) -> list[Any]:
        """Return a shuffled copy of the list.

        Args:
            items: List to shuffle.

        Returns:
            New shuffled list.
        """
        result = items.copy()
        self.rng.shuffle(result)
        return result

    def random_slot_value(
        self,
        slot_type: str,
        domain: str,
        exclude: list[str] | None = None,
    ) -> str:
        """Generate a random slot value based on type and domain.

        Args:
            slot_type: Type of slot (e.g., "city", "date", "number").
            domain: Domain name for context-specific values.
            exclude: Values to exclude from selection.

        Returns:
            A random slot value appropriate for the type.
        """
        exclude = exclude or []

        # Import domain-specific values dynamically
        values = self._get_domain_values(slot_type, domain)
        available = [v for v in values if v not in exclude]

        if not available:
            return values[0] if values else "unknown"

        result: str = self.choice(available)
        return result

    def _get_domain_values(self, slot_type: str, domain: str) -> list[str]:
        """Get available values for a slot type in a domain.

        Args:
            slot_type: Type of slot.
            domain: Domain name.

        Returns:
            List of available values.
        """
        # Default values by type
        defaults: dict[str, list[str]] = {
            "city": ["Madrid", "Barcelona", "Paris", "London", "New York"],
            "date": ["tomorrow", "next Monday", "next week", "in two days"],
            "number": ["1", "2", "3", "4", "5"],
            "string": ["value1", "value2", "value3"],
        }

        return defaults.get(slot_type, defaults["string"])

    def format_template(self, template: str, **kwargs: Any) -> str:
        """Format a template with provided values.

        Args:
            template: Template string with {placeholder} syntax.
            **kwargs: Values to substitute into template.

        Returns:
            Formatted string.
        """
        try:
            return template.format(**kwargs)
        except KeyError:
            return template

    def maybe_add_prefix(
        self,
        message: str,
        prefixes: list[str],
        probability: float = 0.3,
    ) -> str:
        """Optionally add a prefix to a message.

        Args:
            message: Base message.
            prefixes: List of possible prefixes.
            probability: Chance of adding a prefix (0-1).

        Returns:
            Message with or without prefix.
        """
        if self.rng.random() < probability and prefixes:
            prefix = self.choice(prefixes)
            if prefix:
                return f"{prefix}{message}"
        return message
