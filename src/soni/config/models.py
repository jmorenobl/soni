"""Flow and step configuration models.

Core Pydantic models for defining flows, steps, slots, and triggers.
"""

from pydantic import BaseModel, Field

# Import discriminated union step types
from soni.config.steps import (
    ActionStepConfig,
    AnyStepConfig,
    BranchStepConfig,
    CollectStepConfig,
    ConfirmStepConfig,
    SayStepConfig,
    SetStepConfig,
    StepConfig,
    WhileStepConfig,
)


class TriggerConfig(BaseModel):
    """Trigger configuration for a flow."""

    intents: list[str] = Field(
        default_factory=list, description="Example phrases that trigger this flow"
    )


class SlotConfig(BaseModel):
    """Slot definition from YAML.

    Provides metadata for slot validation and NLU extraction.
    """

    type: str = Field(default="string", description="Data type: string, float, date, etc.")
    prompt: str = Field(default="", description="Prompt to ask user for this slot")
    validator: str | None = Field(default=None, description="Validator function name")
    validation_error_message: str | None = Field(
        default=None, description="Message shown when validation fails"
    )
    required: bool = Field(default=True, description="Whether this slot must be filled")
    description: str = Field(default="", description="Human-readable description for NLU")
    examples: list[str] = Field(
        default_factory=list, description="Example valid values for NLU extraction"
    )


class FlowConfig(BaseModel):
    """Configuration for a single flow."""

    description: str
    steps: list[StepConfig] = Field(default_factory=list)
    trigger: TriggerConfig | None = None

    @property
    def trigger_intents(self) -> list[str]:
        """Get trigger intents or empty list."""
        return self.trigger.intents if self.trigger else []


# Re-export step types for convenience
__all__ = [
    "TriggerConfig",
    "SlotConfig",
    "FlowConfig",
    "StepConfig",
    "AnyStepConfig",
    "SayStepConfig",
    "CollectStepConfig",
    "ActionStepConfig",
    "BranchStepConfig",
    "ConfirmStepConfig",
    "WhileStepConfig",
    "SetStepConfig",
]
