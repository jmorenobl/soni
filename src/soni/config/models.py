"""Configuration models for Soni v2 M1."""

from typing import Annotated, Literal

from pydantic import BaseModel, Field

# DSL Version constants
SUPPORTED_VERSIONS = frozenset({"1.0"})
CURRENT_VERSION = "1.0"


class SayStepConfig(BaseModel):
    """Configuration for say steps."""

    step: str = Field(description="Step identifier")
    type: Literal["say"] = "say"
    message: str = Field(description="Message to display")


class CollectStepConfig(BaseModel):
    """Configuration for collect steps."""

    step: str = Field(description="Step identifier")
    type: Literal["collect"] = "collect"
    slot: str = Field(description="Slot to fill")
    message: str = Field(description="Prompt message")


class SetStepConfig(BaseModel):
    """Configuration for set steps."""

    step: str = Field(description="Step identifier")
    type: Literal["set"] = "set"
    slots: dict[str, str | int | float | bool] = Field(description="Values to assign")
    condition: str | None = Field(default=None, description="Optional condition")


class BranchStepConfig(BaseModel):
    """Configuration for branch steps."""

    step: str = Field(description="Step identifier")
    type: Literal["branch"] = "branch"
    slot: str | None = Field(default=None, description="Slot to check")
    evaluate: str | None = Field(default=None, description="Expression to evaluate")
    cases: dict[str, str] = Field(description="Branching cases")


# Steps that can be defined inline (no nested while to avoid infinite recursion)
InlineStepConfig = Annotated[
    SayStepConfig | CollectStepConfig | SetStepConfig | BranchStepConfig,
    Field(discriminator="type"),
]


class WhileStepConfig(BaseModel):
    """Configuration for while loop steps.

    While loops are guard nodes that:
    1. Evaluate a condition
    2. If TRUE: route to first step in `do` block
    3. If FALSE: route to `exit_to` (or next step after while)

    The last step in `do` block automatically loops back to the guard.

    The `do` block can contain:
    - Step names (str) referencing steps defined elsewhere
    - Inline step definitions (more intuitive, keeps loop body together)
    """

    step: str = Field(description="Step identifier")
    type: Literal["while"] = "while"
    condition: str = Field(description="Loop condition expression")
    do: list[str | InlineStepConfig] = Field(
        description="Steps to execute in loop body (names or inline definitions)",
        min_length=1,
    )
    exit_to: str | None = Field(
        default=None, description="Step to go to on exit (auto-calculated if not set)"
    )

    def get_do_step_names(self) -> list[str]:
        """Get step names from do block (resolving inline definitions)."""
        return [s if isinstance(s, str) else s.step for s in self.do]

    def get_inline_steps(self) -> list[InlineStepConfig]:
        """Get inline step definitions from do block."""
        return [s for s in self.do if not isinstance(s, str)]


class ActionStepConfig(BaseModel):
    """Configuration for action steps (M5).

    Actions execute external handlers and optionally map outputs to slots.
    """

    step: str = Field(description="Step identifier")
    type: Literal["action"] = "action"
    call: str = Field(description="Name of action handler to call")
    map_outputs: dict[str, str] | None = Field(
        default=None, description="Map action outputs to slot names"
    )


StepConfig = Annotated[
    SayStepConfig | CollectStepConfig | SetStepConfig | BranchStepConfig | WhileStepConfig | ActionStepConfig,
    Field(discriminator="type"),
]


class FlowConfig(BaseModel):
    """Configuration for a flow."""

    description: str = ""
    steps: list[StepConfig] = Field(default_factory=list)


class SoniConfig(BaseModel):
    """Root configuration with DSL versioning."""

    version: str = Field(default=CURRENT_VERSION, description="DSL version")
    flows: dict[str, FlowConfig] = Field(default_factory=dict)

    def model_post_init(self, __context: object) -> None:
        """Validate DSL version after initialization."""
        if self.version not in SUPPORTED_VERSIONS:
            raise ValueError(
                f"Unsupported DSL version: {self.version}. "
                f"Supported: {', '.join(sorted(SUPPORTED_VERSIONS))}"
            )
