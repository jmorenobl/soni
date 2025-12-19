"""Settings configuration models.

Global settings for models, persistence, and other runtime configuration.
"""

from typing import Literal

from pydantic import BaseModel, Field

from soni.config.patterns import PatternBehaviorsConfig

# LangGraph durability modes for checkpoint persistence
DurabilityMode = Literal["sync", "async", "exit"]


class NLUModelConfig(BaseModel):
    """NLU model configuration."""

    provider: str = Field(default="openai", description="Model provider (openai, anthropic, etc.)")
    model: str = Field(default="gpt-4o-mini", description="Model identifier")
    temperature: float = Field(default=0.1, description="Temperature for generation")
    use_reasoning: bool = Field(default=False, description="Use ChainOfThought for reasoning")


class ModelsConfig(BaseModel):
    """Models configuration section."""

    nlu: NLUModelConfig = Field(default_factory=NLUModelConfig)


class PersistenceConfig(BaseModel):
    """Persistence configuration."""

    backend: str = Field(default="sqlite", description="Backend type: sqlite, postgres, redis")
    path: str = Field(default="soni.db", description="Connection path/string")


class SettingsConfig(BaseModel):
    """Global settings configuration."""

    models: ModelsConfig = Field(default_factory=ModelsConfig)
    persistence: PersistenceConfig = Field(default_factory=PersistenceConfig)
    patterns: PatternBehaviorsConfig = Field(default_factory=PatternBehaviorsConfig)

    durability: DurabilityMode = Field(
        default="async",
        description=(
            "Checkpoint durability mode for LangGraph runtime. "
            "Controls when checkpoints are persisted: "
            "'sync' = before next step (safest, slower), "
            "'async' = while next step runs (default, balanced), "
            "'exit' = only on exit (fastest, risky)"
        ),
    )
