"""Pattern behavior configuration models.

Configures how built-in conversational patterns behave.
"""

from pydantic import BaseModel, Field


class ConfirmationPatternConfig(BaseModel):
    """Configuration for confirmation pattern behavior."""

    modification_handling: str = Field(
        default="update_and_reprompt",
        description="Behavior when user modifies slot during confirmation: 'update_and_reprompt' or 'update_and_confirm'",
    )
    update_acknowledgment: str = Field(
        default="Updated.", description="Message when slot is updated"
    )
    retry_message: str = Field(
        default="Please confirm: {prompt}", description="Message template for retry"
    )
    max_retries: int = Field(default=3, ge=1, le=10, description="Max confirmation retries")


class CorrectionPatternConfig(BaseModel):
    """Configuration for correction pattern behavior."""

    enabled: bool = True
    response_template: str = Field(
        default="Updated {slot} to {value}.", description="Response after correction"
    )
    revalidate: bool = True


class ClarificationPatternConfig(BaseModel):
    """Configuration for clarification pattern behavior."""

    enabled: bool = True
    response_template: str = Field(default="{explanation}", description="Response template")
    fallback_message: str = Field(
        default="I need this information to proceed.",
        description="Fallback when no explanation available",
    )


class CancellationPatternConfig(BaseModel):
    """Configuration for cancellation pattern behavior."""

    enabled: bool = True
    require_confirmation: bool = Field(
        default=False, description="Require confirmation before cancelling"
    )
    response_message: str = Field(
        default="Okay, I've cancelled that.", description="Response after cancellation"
    )


class HumanHandoffPatternConfig(BaseModel):
    """Configuration for human handoff pattern behavior."""

    enabled: bool = True
    message: str = Field(default="Transferring you to an agent...", description="Handoff message")


class PatternBehaviorsConfig(BaseModel):
    """Configurable behaviors for conversation patterns."""

    confirmation: ConfirmationPatternConfig = Field(default_factory=ConfirmationPatternConfig)
    correction: CorrectionPatternConfig = Field(default_factory=CorrectionPatternConfig)
    clarification: ClarificationPatternConfig = Field(default_factory=ClarificationPatternConfig)
    cancellation: CancellationPatternConfig = Field(default_factory=CancellationPatternConfig)
    human_handoff: HumanHandoffPatternConfig = Field(default_factory=HumanHandoffPatternConfig)
