"""Base protocol for node factories."""

from typing import Protocol

from soni.config.models import StepConfig
from soni.core.types import NodeFunction


class NodeFactory(Protocol):
    """Protocol for step type node factories (OCP: Open for extension)."""

    def create(
        self,
        step: StepConfig,
        all_steps: list[StepConfig] | None = None,
        step_index: int | None = None,
    ) -> NodeFunction:
        """Create a node function for the given step config."""
        ...
