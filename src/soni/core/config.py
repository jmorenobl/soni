"""Configuration models for Soni."""

from pathlib import Path

import yaml
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


class SoniConfig(BaseModel):
    """Main configuration model."""

    version: str = "1.0"
    settings: SettingsConfig = Field(default_factory=SettingsConfig)
    flows: dict[str, FlowConfig] = Field(default_factory=dict)

    @classmethod
    def from_yaml(cls, path: str | Path) -> "SoniConfig":
        """Load configuration from YAML file."""
        return ConfigLoader.load(path)


class ConfigLoader:
    """Loader for Soni configuration files."""

    @staticmethod
    def load(path: str | Path) -> SoniConfig:
        """Load and validate configuration from YAML file.

        Args:
            path: Path to YAML configuration file.

        Returns:
            Validated SoniConfig object.

        Raises:
            ConfigError: If file not found or invalid format.
        """
        path = Path(path)
        if not path.exists():
            # Need to import ConfigError locally to avoid circular import if defined in errors.py
            # which might import config... actually config.py is usually low level dependency.
            from soni.core.errors import ConfigError

            raise ConfigError(f"Configuration file not found: {path}")

        try:
            with open(path, encoding="utf-8") as f:
                data = yaml.safe_load(f)

            return SoniConfig(**data)
        except yaml.YAMLError as e:
            from soni.core.errors import ConfigError

            raise ConfigError(f"Error parsing YAML: {e}") from e
        except Exception as e:
            from soni.core.errors import ConfigError

            raise ConfigError(f"Invalid configuration: {e}") from e
