"""Configuration models for Soni.

Defined using Pydantic for validation and YAML serialization support.
Follows strict typing and SOLID principles.
"""

from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field


class StepConfig(BaseModel):
    """Configuration for a single step in a flow."""

    step: str
    type: str
    slot: str | None = None
    message: str | None = None
    slots: list[str] | dict[str, Any] | None = None  # For collect (list) or set (dict)
    call: str | None = None
    condition: str | None = None
    evaluate: str | None = None  # For branch: expression to evaluate (alternative to slot)
    do: list[str] | None = None
    cases: dict[str, str] | None = None
    on_confirm: str | None = None
    on_deny: str | None = None
    jump_to: str | None = None
    exit_to: str | None = None  # For while loops: explicit exit target
    max_retries: int | None = None

    # While loop metadata (set by WhileNodeFactory)
    loop_body_start: str | None = None
    loop_body_end: str | None = None
    calculated_exit_target: str | None = None
    map_outputs: dict[str, str] | None = None  # Map action outputs: {action_key: slot_name}


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
    trigger: TriggerConfig | None = None  # Trigger examples

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


# --- Pattern Configurations ---


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


class SettingsConfig(BaseModel):
    """Global settings configuration."""

    models: ModelsConfig = Field(default_factory=ModelsConfig)
    persistence: PersistenceConfig = Field(default_factory=PersistenceConfig)
    patterns: PatternBehaviorsConfig = Field(default_factory=PatternBehaviorsConfig)


class SoniConfig(BaseModel):
    """Main configuration model."""

    version: str = "1.0"
    settings: SettingsConfig = Field(default_factory=SettingsConfig)
    slots: dict[str, SlotConfig] = Field(default_factory=dict)
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
