"""Validators for dialogue flow configurations"""

from typing import Any

from soni.core.config import SoniConfig
from soni.core.errors import ValidationError


class FlowValidator:
    """Validates dialogue flow configurations."""

    def __init__(self, config: SoniConfig):
        """
        Initialize FlowValidator with configuration.

        Args:
            config: Soni configuration containing flows, slots, and actions
        """
        self.config = config

    def validate_flow(self, flow_name: str) -> None:
        """
        Validate a flow configuration.

        Args:
            flow_name: Name of the flow to validate

        Raises:
            ValidationError: If flow configuration is invalid
        """
        if flow_name not in self.config.flows:
            raise ValidationError(
                f"Flow '{flow_name}' not found in configuration",
                field="flow_name",
                value=flow_name,
                context={"available_flows": list(self.config.flows.keys())},
            )

        flow_config = self.config.flows[flow_name]

        # Validate flow structure
        self._validate_flow_structure(flow_config)
        self._validate_flow_slots(flow_config)
        self._validate_flow_actions(flow_config)

    def _validate_flow_structure(self, flow_config: Any) -> None:
        """
        Validate basic flow structure.

        Args:
            flow_config: Flow configuration to validate

        Raises:
            ValidationError: If flow structure is invalid
        """
        if not hasattr(flow_config, "steps"):
            raise ValidationError(
                "Flow must have 'steps' attribute",
                field="steps",
                context={"flow_config": str(flow_config)},
            )

        if not isinstance(flow_config.steps, list):
            raise ValidationError(
                f"Flow 'steps' must be a list, got {type(flow_config.steps).__name__}",
                field="steps",
                value=flow_config.steps,
            )

    def _validate_flow_slots(self, flow_config: Any) -> None:
        """
        Validate that referenced slots exist in config.

        Args:
            flow_config: Flow configuration to validate

        Raises:
            ValidationError: If referenced slot is not defined
        """
        for step in flow_config.steps:
            if step.type == "collect" and step.slot:
                if step.slot not in self.config.slots:
                    raise ValidationError(
                        f"Flow references slot '{step.slot}' which is not defined",
                        field="slot",
                        value=step.slot,
                        context={
                            "step": step.step if hasattr(step, "step") else None,
                            "available_slots": list(self.config.slots.keys()),
                        },
                    )

    def _validate_flow_actions(self, flow_config: Any) -> None:
        """
        Validate that referenced actions exist in config.

        Args:
            flow_config: Flow configuration to validate

        Raises:
            ValidationError: If referenced action is not defined
        """
        for step in flow_config.steps:
            if step.type == "action" and step.call:
                if step.call not in self.config.actions:
                    raise ValidationError(
                        f"Flow references action '{step.call}' which is not defined",
                        field="action",
                        value=step.call,
                        context={
                            "step": step.step if hasattr(step, "step") else None,
                            "available_actions": list(self.config.actions.keys()),
                        },
                    )
