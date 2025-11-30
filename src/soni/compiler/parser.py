"""Step parser for validating and structuring flow steps"""

import logging
from dataclasses import dataclass
from typing import Any

from soni.core.config import StepConfig
from soni.core.errors import CompilationError

logger = logging.getLogger(__name__)


@dataclass
class ParsedStep:
    """Parsed and validated step representation."""

    step_id: str
    step_type: str  # "collect", "action", etc.
    config: dict[str, Any]

    def __post_init__(self) -> None:
        """Validate parsed step structure."""
        if not self.step_id:
            raise ValueError("step_id cannot be empty")
        if not self.step_type:
            raise ValueError("step_type cannot be empty")


class StepParser:
    """Parses and validates flow steps from YAML configuration."""

    def __init__(self) -> None:
        """Initialize StepParser."""
        self.supported_types = {"collect", "action", "branch"}

    def parse(self, steps: list[StepConfig]) -> list[ParsedStep]:
        """
        Parse and validate a list of steps.

        Args:
            steps: List of StepConfig from YAML

        Returns:
            List of ParsedStep objects

        Raises:
            CompilationError: If parsing fails with clear error message
        """
        parsed_steps: list[ParsedStep] = []

        for idx, step in enumerate(steps, start=1):
            try:
                parsed = self._parse_step(step, idx)
                parsed_steps.append(parsed)
            except ValueError as e:
                raise CompilationError(
                    f"Error parsing step {idx} ('{step.step}'): {str(e)}",
                    step_index=idx,
                    step_name=step.step,
                ) from e

        return parsed_steps

    def _parse_step(self, step: StepConfig, index: int) -> ParsedStep:
        """
        Parse a single step.

        Args:
            step: StepConfig to parse
            index: 1-based index for error messages

        Returns:
            ParsedStep object

        Raises:
            ValueError: If step is invalid
        """
        # Validate step_id
        if not step.step or not step.step.strip():
            raise ValueError("Step must have a non-empty 'step' identifier")

        # Validate step_type
        if not step.type:
            raise ValueError("Step must specify a 'type'")

        if step.type not in self.supported_types:
            raise ValueError(
                f"Unsupported step type '{step.type}'. "
                f"Supported types: {', '.join(sorted(self.supported_types))}"
            )

        # Type-specific validation
        config: dict[str, Any] = {}

        if step.type == "collect":
            if not step.slot:
                raise ValueError(f"Step '{step.step}' of type 'collect' must specify a 'slot'")
            config["slot_name"] = step.slot

        elif step.type == "action":
            if not step.call:
                raise ValueError(f"Step '{step.step}' of type 'action' must specify a 'call'")
            config["action_name"] = step.call
            if step.map_outputs:
                config["map_outputs"] = step.map_outputs

        elif step.type == "branch":
            if not step.input:
                raise ValueError(f"Step '{step.step}' of type 'branch' must specify an 'input'")
            if not step.cases:
                raise ValueError(f"Step '{step.step}' of type 'branch' must specify 'cases'")
            if not isinstance(step.cases, dict):
                raise ValueError(
                    f"Step '{step.step}' of type 'branch' must have 'cases' as a dictionary"
                )
            config["input"] = step.input
            config["cases"] = step.cases

        # Parse jump_to for any step type
        if step.jump_to:
            if not step.jump_to.strip():
                raise ValueError(f"Step '{step.step}' has empty 'jump_to' field")
            config["jump_to"] = step.jump_to

        return ParsedStep(
            step_id=step.step,
            step_type=step.type,
            config=config,
        )
