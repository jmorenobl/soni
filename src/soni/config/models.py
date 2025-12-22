"""Configuration models for Soni v2 M8."""

from typing import Annotated, Any, Literal

from pydantic import BaseModel, Field

# DSL Version constants
SUPPORTED_VERSIONS = frozenset({"1.0"})
CURRENT_VERSION = "1.0"


class SayStepConfig(BaseModel):
    """Configuration for say steps."""

    step: str = Field(description="Step identifier")
    type: Literal["say"] = "say"
    message: str = Field(description="Message to display")
    rephrase: bool = Field(default=True, description="Whether to rephrase with LLM")


class CollectStepConfig(BaseModel):
    """Configuration for collect steps."""

    step: str = Field(description="Step identifier")
    type: Literal["collect"] = "collect"
    slot: str = Field(description="Slot to fill")
    message: str = Field(description="Prompt message")
    validator: str | None = Field(default=None, description="Validator function name")
    validation_error_message: str | None = Field(
        default=None, description="Error message on validation failure"
    )
    rephrase: bool = Field(default=True, description="Whether to rephrase with LLM")


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


class LinkStepConfig(BaseModel):
    """Configuration for link steps (M6).

    Link transfers control to another flow without return.
    Current flow is popped, target flow is pushed.
    """

    step: str = Field(description="Step identifier")
    type: Literal["link"] = "link"
    target: str = Field(description="Flow to link to")


class CallStepConfig(BaseModel):
    """Configuration for call steps (M6).

    Call invokes a subflow and returns when it completes.
    Current flow stays on stack, target flow is pushed on top.
    """

    step: str = Field(description="Step identifier")
    type: Literal["call"] = "call"
    target: str = Field(description="Subflow to call")


class ConfirmStepConfig(BaseModel):
    """Configuration for confirm steps (M7).

    Validates a slot value with the user before proceeding.
    """

    step: str = Field(description="Step identifier")
    type: Literal["confirm"] = "confirm"
    slot: str = Field(description="Slot to confirm")
    message: str | None = Field(default=None, description="Confirmation prompt")
    on_confirm: str | None = Field(
        default=None, description="Step to go to on confirm (defaults to next)"
    )
    on_deny: str | None = Field(default=None, description="Step to go to on deny")
    rephrase: bool = Field(default=True, description="Whether to rephrase with LLM")


StepConfig = Annotated[
    SayStepConfig
    | CollectStepConfig
    | SetStepConfig
    | BranchStepConfig
    | WhileStepConfig
    | ActionStepConfig
    | LinkStepConfig
    | CallStepConfig
    | ConfirmStepConfig,
    Field(discriminator="type"),
]

# Type alias for supported rephrasing tones
RephraseTone = Literal["friendly", "professional", "formal"]


class LLMConfig(BaseModel):
    """Configuration for LLM provider."""

    provider: Literal["openai", "anthropic", "fake"] = Field(
        default="openai", description="LLM provider"
    )
    model: str = Field(default="gpt-4o-mini", description="Model identifier")
    api_key: str | None = Field(default=None, description="API key (optional)")


class PersistenceConfig(BaseModel):
    """Configuration for persistence backend."""

    backend: Literal["memory", "sqlite", "postgres"] = Field(
        default="memory", description="Persistence backend type"
    )
    path: str = Field(default=":memory:", description="File path or connection string")
    cleanup_interval: int = Field(default=3600, description="Cleanup interval in seconds")


class Settings(BaseModel):
    """Runtime settings for Soni."""

    rephrase_responses: bool = Field(
        default=False, description="Enable LLM rephrasing of template responses"
    )
    rephrase_tone: RephraseTone = Field(
        default="friendly", description="Tone for rephrased responses"
    )
    llm: LLMConfig = Field(default_factory=LLMConfig, description="LLM settings")
    persistence: PersistenceConfig = Field(
        default_factory=PersistenceConfig, description="Persistence settings"
    )


class SlotDefinition(BaseModel):
    """Configuration for a slot definition in trigger."""

    name: str = Field(description="Slot name")
    type: str = Field(default="string", description="Slot type")
    description: str | None = Field(default=None, description="Slot description")


class TriggerConfig(BaseModel):
    """Configuration for flow triggering."""

    intents: list[str] = Field(default_factory=list, description="Trigger phrases/intents")
    slots: list[SlotDefinition | dict[str, Any]] = Field(
        default_factory=list, description="Slots to extract on trigger"
    )


class FlowConfig(BaseModel):
    """Configuration for a flow."""

    description: str = ""
    trigger: TriggerConfig | None = Field(default=None, description="Trigger configuration")
    steps: list[StepConfig] = Field(default_factory=list)


class SoniConfig(BaseModel):
    """Root configuration with DSL versioning."""

    version: str = Field(default=CURRENT_VERSION, description="DSL version")
    flows: dict[str, FlowConfig] = Field(default_factory=dict)
    settings: Settings = Field(default_factory=Settings)

    def model_post_init(self, __context: object) -> None:
        """Validate DSL version after initialization."""
        if self.version not in SUPPORTED_VERSIONS:
            raise ValueError(
                f"Unsupported DSL version: {self.version}. "
                f"Supported: {', '.join(sorted(SUPPORTED_VERSIONS))}"
            )
