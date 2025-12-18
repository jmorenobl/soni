"""Step configuration models with discriminated unions.

Type-safe step configurations using Pydantic discriminated unions.
Each step type has its own class with only the relevant fields.

For backwards compatibility, GenericStepConfig is also provided.
"""

from typing import Annotated, Any, Literal

from pydantic import BaseModel, Field


class BaseStepConfig(BaseModel):
    """Base configuration shared by all step types."""

    step: str = Field(description="Unique step identifier within the flow")


class SayStepConfig(BaseStepConfig):
    """Configuration for 'say' steps - display a message."""

    type: Literal["say"] = "say"
    message: str = Field(description="Message to display (supports {slot} substitution)")


class CollectStepConfig(BaseStepConfig):
    """Configuration for 'collect' steps - collect slot value from user."""

    type: Literal["collect"] = "collect"
    slot: str = Field(description="Slot name to collect")
    message: str | None = Field(default=None, description="Prompt message for the slot")


class ActionStepConfig(BaseStepConfig):
    """Configuration for 'action' steps - call a registered action."""

    type: Literal["action"] = "action"
    call: str = Field(description="Action name to call")
    map_outputs: dict[str, str] | None = Field(
        default=None, description="Map action outputs: {action_key: slot_name}"
    )


class BranchStepConfig(BaseStepConfig):
    """Configuration for 'branch' steps - conditional routing."""

    type: Literal["branch"] = "branch"
    slot: str | None = Field(default=None, description="Slot to evaluate for branching")
    evaluate: str | None = Field(
        default=None, description="Expression to evaluate (alternative to slot)"
    )
    cases: dict[str, str] = Field(description="Mapping of values to target steps")


class ConfirmStepConfig(BaseStepConfig):
    """Configuration for 'confirm' steps - confirmation prompts."""

    type: Literal["confirm"] = "confirm"
    slot: str = Field(description="Slot containing value to confirm")
    message: str | None = Field(default=None, description="Confirmation prompt")
    on_confirm: str | None = Field(default=None, description="Step to go on confirm")
    on_deny: str | None = Field(default=None, description="Step to go on deny")
    max_retries: int | None = Field(default=None, description="Max confirmation retries")


class WhileStepConfig(BaseStepConfig):
    """Configuration for 'while' steps - loop construct."""

    type: Literal["while"] = "while"
    condition: str = Field(description="Condition expression for the loop")
    do: list[str] = Field(description="Steps to execute in the loop body")
    exit_to: str | None = Field(default=None, description="Explicit exit target step")

    # Metadata set by compiler (not from YAML)
    loop_body_start: str | None = Field(default=None, description="First step of loop body")
    loop_body_end: str | None = Field(default=None, description="Last step of loop body")
    calculated_exit_target: str | None = Field(default=None, description="Calculated exit target")


class SetStepConfig(BaseStepConfig):
    """Configuration for 'set' steps - set slot values programmatically."""

    type: Literal["set"] = "set"
    slots: dict[str, Any] = Field(description="Slot assignments: {slot_name: value_or_expression}")
    condition: str | None = Field(default=None, description="Optional condition for execution")


class GenericStepConfig(BaseModel):
    """Generic step configuration for backwards compatibility.

    This class accepts all possible fields from any step type.
    Use typed step configs (SayStepConfig, etc.) for type safety.
    """

    step: str
    type: str
    slot: str | None = None
    message: str | None = None
    slots: list[str] | dict[str, Any] | None = None
    call: str | None = None
    condition: str | None = None
    evaluate: str | None = None
    do: list[str] | None = None
    cases: dict[str, str] | None = None
    on_confirm: str | None = None
    on_deny: str | None = None
    jump_to: str | None = None
    exit_to: str | None = None
    max_retries: int | None = None
    loop_body_start: str | None = None
    loop_body_end: str | None = None
    calculated_exit_target: str | None = None
    map_outputs: dict[str, str] | None = None


# Type alias for any step config (typed or generic)
AnyStepConfig = (
    SayStepConfig
    | CollectStepConfig
    | ActionStepConfig
    | BranchStepConfig
    | ConfirmStepConfig
    | WhileStepConfig
    | SetStepConfig
    | GenericStepConfig
)

# StepConfig is the GenericStepConfig for full backwards compatibility
# This allows existing code to work without changes
StepConfig = GenericStepConfig

# Discriminated union (for strict typing when needed)
TypedStepConfig = Annotated[
    SayStepConfig
    | CollectStepConfig
    | ActionStepConfig
    | BranchStepConfig
    | ConfirmStepConfig
    | WhileStepConfig
    | SetStepConfig,
    Field(discriminator="type"),
]


__all__ = [
    "BaseStepConfig",
    "SayStepConfig",
    "CollectStepConfig",
    "ActionStepConfig",
    "BranchStepConfig",
    "ConfirmStepConfig",
    "WhileStepConfig",
    "SetStepConfig",
    "GenericStepConfig",
    "StepConfig",  # Alias to GenericStepConfig for backwards compat
    "TypedStepConfig",  # Discriminated union for strict typing
    "AnyStepConfig",
]
