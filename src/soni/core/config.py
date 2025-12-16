"""Configuration models for Soni."""

from pydantic import BaseModel, Field


class StepConfig(BaseModel):
    """Configuration for a flow step."""

    step: str
    type: str  # collect, action, branch, confirm, say, while
    slot: str | None = None
    call: str | None = None
    message: str | None = None
    input: str | None = None
    cases: dict[str, str] | None = None
    condition: str | None = None
    do: list[str] | None = None
    jump_to: str | None = None
    max_retries: int | None = None  # For confirm nodes


class FlowConfig(BaseModel):
    """Configuration for a single flow."""

    description: str
    steps: list[StepConfig] = Field(default_factory=list)
    process: list[StepConfig] | None = None  # Keep for backward compatibility if needed

    @property
    def steps_or_process(self) -> list[StepConfig]:
        """Return steps from either 'steps' or 'process' field (for backward compatibility)."""
        return self.process or self.steps or []


class SoniConfig(BaseModel):
    """Main configuration model."""

    version: str = "1.0"
    flows: dict[str, FlowConfig] = Field(default_factory=dict)
