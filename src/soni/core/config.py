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
    map_outputs: dict[str, str] | None = None  # Map action outputs: {action_key: slot_name}


class TriggerConfig(BaseModel):
    """Trigger configuration for a flow."""

    intents: list[str] = Field(
        default_factory=list, description="Example phrases that trigger this flow"
    )


class FlowConfig(BaseModel):
    """Configuration for a single flow."""

    description: str
    steps: list[StepConfig] = Field(default_factory=list)
    process: list[StepConfig] | None = None  # Keep for backward compatibility if needed
    trigger: TriggerConfig | None = None  # Trigger examples

    @property
    def steps_or_process(self) -> list[StepConfig]:
        """Return steps from either 'steps' or 'process' field (for backward compatibility)."""
        return self.process or self.steps or []

    @property
    def trigger_intents(self) -> list[str]:
        """Get trigger intents or empty list."""
        return self.trigger.intents if self.trigger else []


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
    """Loader for Soni configuration files.

    Supports both single YAML files and directories containing multiple YAML files.
    When loading from a directory, all .yaml/.yml files are merged in alphabetical order.
    """

    @staticmethod
    def load(path: str | Path) -> SoniConfig:
        """Load and validate configuration from YAML file or directory.

        Args:
            path: Path to YAML configuration file or directory containing YAML files.

        Returns:
            Validated SoniConfig object.

        Raises:
            ConfigError: If file/directory not found or invalid format.
        """
        path = Path(path)
        if not path.exists():
            from soni.core.errors import ConfigError

            raise ConfigError(f"Configuration file not found: {path}")

        try:
            if path.is_dir():
                data = ConfigLoader._load_directory(path)
            else:
                data = ConfigLoader._load_file(path)

            return SoniConfig(**data)
        except yaml.YAMLError as e:
            from soni.core.errors import ConfigError

            raise ConfigError(f"Error parsing YAML: {e}") from e
        except Exception as e:
            from soni.core.errors import ConfigError

            raise ConfigError(f"Invalid configuration: {e}") from e

    @staticmethod
    def _load_file(path: Path) -> dict:
        """Load a single YAML file."""
        with open(path, encoding="utf-8") as f:
            return yaml.safe_load(f) or {}

    @staticmethod
    def _load_directory(directory: Path) -> dict:
        """Load and merge all YAML files from a directory.

        Files are loaded in alphabetical order. Later files override earlier ones
        for top-level keys, but nested dicts (flows, slots, actions) are merged.
        """
        merged: dict = {}
        yaml_files = sorted(directory.glob("*.yaml")) + sorted(directory.glob("*.yml"))

        if not yaml_files:
            from soni.core.errors import ConfigError

            raise ConfigError(f"No YAML files found in directory: {directory}")

        for yaml_file in yaml_files:
            file_data = ConfigLoader._load_file(yaml_file)
            merged = ConfigLoader._deep_merge(merged, file_data)

        return merged

    @staticmethod
    def _deep_merge(base: dict, override: dict) -> dict:
        """Deep merge two dictionaries.

        For dict values, recursively merge. For other types, override replaces base.
        """
        result = base.copy()

        for key, value in override.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = ConfigLoader._deep_merge(result[key], value)
            else:
                result[key] = value

        return result
