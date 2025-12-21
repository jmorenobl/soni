"""Configuration models for Soni v2 M1."""

from typing import Annotated

from pydantic import BaseModel, Field

# DSL Version constants
SUPPORTED_VERSIONS = frozenset({"1.0"})
CURRENT_VERSION = "1.0"


class SayStepConfig(BaseModel):
    """Configuration for say steps."""
    step: str = Field(description="Step identifier")
    type: str = "say"
    message: str = Field(description="Message to display")


class FlowConfig(BaseModel):
    """Configuration for a flow."""
    description: str = ""
    steps: list[SayStepConfig] = Field(default_factory=list)


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

StepConfig = Annotated[
    SayStepConfig,
    Field(discriminator="type"),
]
