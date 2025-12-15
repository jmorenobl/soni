"""Configuration loading and validation for Soni Framework."""

from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field

from soni.core.errors import ConfigurationError, ValidationError


class ConfigLoader:
    """Loads and validates Soni configuration from YAML files.

    This class handles:
    - Loading YAML files safely
    - Validating required fields
    - Providing clear error messages
    """

    REQUIRED_FIELDS = ["version"]
    REQUIRED_SECTIONS = ["settings", "flows", "slots", "actions"]

    @staticmethod
    def load(path: str | Path) -> dict[str, Any]:
        """Load configuration from a YAML file.

        Args:
            path: Path to the YAML configuration file

        Returns:
            Dictionary containing the parsed configuration

        Raises:
            ConfigurationError: If file cannot be loaded or parsed
        """
        path_obj = Path(path)

        # Check if file exists
        if not path_obj.exists():
            raise ConfigurationError(
                f"Configuration file not found: {path}",
                context={"path": str(path)},
            )

        # Check if it's a file
        if not path_obj.is_file():
            raise ConfigurationError(
                f"Path is not a file: {path}",
                context={"path": str(path)},
            )

        # Load YAML
        try:
            with open(path_obj, encoding="utf-8") as f:
                config = yaml.safe_load(f)
        except yaml.YAMLError as e:
            raise ConfigurationError(
                f"Invalid YAML syntax in {path}: {e}",
                context={"path": str(path), "yaml_error": str(e)},
            ) from e
        except OSError as e:
            raise ConfigurationError(
                f"Error reading file {path}: {e}",
                context={"path": str(path), "io_error": str(e)},
            ) from e

        # Validate basic structure
        if config is None:
            raise ConfigurationError(
                f"Configuration file is empty: {path}",
                context={"path": str(path)},
            )

        if not isinstance(config, dict):
            raise ConfigurationError(
                f"Configuration must be a dictionary, got {type(config).__name__}",
                context={"path": str(path), "type": type(config).__name__},
            )

        return config

    @staticmethod
    def validate(config: dict[str, Any]) -> list[ValidationError]:
        """Validate configuration structure.

        Args:
            config: Configuration dictionary to validate

        Returns:
            List of ValidationError objects (empty if valid)
        """
        errors: list[ValidationError] = []

        # Delegate to specialized validation methods
        errors.extend(ConfigLoader._validate_required_fields(config))
        errors.extend(ConfigLoader._validate_version(config))
        errors.extend(ConfigLoader._validate_settings(config))
        errors.extend(ConfigLoader._validate_flows(config))
        errors.extend(ConfigLoader._validate_slots(config))
        errors.extend(ConfigLoader._validate_actions(config))

        return errors

    @staticmethod
    def _validate_required_fields(config: dict[str, Any]) -> list[ValidationError]:
        """Validate required top-level fields."""
        errors: list[ValidationError] = []

        # Check required top-level fields
        for field in ConfigLoader.REQUIRED_FIELDS:
            if field not in config:
                errors.append(
                    ValidationError(
                        f"Missing required field: '{field}'",
                        field=field,
                        context={"config_keys": list(config.keys())},
                    ),
                )

        # Check required sections (warn if missing, but don't fail for MVP)
        for section in ConfigLoader.REQUIRED_SECTIONS:
            if section not in config:
                errors.append(
                    ValidationError(
                        f"Missing recommended section: '{section}'",
                        field=section,
                        context={"config_keys": list(config.keys())},
                    ),
                )

        return errors

    @staticmethod
    def _validate_version(config: dict[str, Any]) -> list[ValidationError]:
        """Validate version field."""
        errors: list[ValidationError] = []

        if "version" in config:
            version = config["version"]
            if not isinstance(version, str):
                errors.append(
                    ValidationError(
                        f"Field 'version' must be a string, got {type(version).__name__}",
                        field="version",
                        value=version,
                    ),
                )

        return errors

    @staticmethod
    def _validate_settings(config: dict[str, Any]) -> list[ValidationError]:
        """Validate settings section."""
        errors: list[ValidationError] = []

        if "settings" in config:
            settings = config["settings"]
            if not isinstance(settings, dict):
                errors.append(
                    ValidationError(
                        f"Section 'settings' must be a dictionary, got {type(settings).__name__}",
                        field="settings",
                        value=settings,
                    ),
                )

        return errors

    @staticmethod
    def _validate_flows(config: dict[str, Any]) -> list[ValidationError]:
        """Validate flows section."""
        errors: list[ValidationError] = []

        if "flows" in config:
            flows = config["flows"]
            if not isinstance(flows, dict):
                errors.append(
                    ValidationError(
                        f"Section 'flows' must be a dictionary, got {type(flows).__name__}",
                        field="flows",
                        value=flows,
                    ),
                )

        return errors

    @staticmethod
    def _validate_slots(config: dict[str, Any]) -> list[ValidationError]:
        """Validate slots section."""
        errors: list[ValidationError] = []

        if "slots" in config:
            slots = config["slots"]
            if not isinstance(slots, dict):
                errors.append(
                    ValidationError(
                        f"Section 'slots' must be a dictionary, got {type(slots).__name__}",
                        field="slots",
                        value=slots,
                    ),
                )

        return errors

    @staticmethod
    def _validate_actions(config: dict[str, Any]) -> list[ValidationError]:
        """Validate actions section."""
        errors: list[ValidationError] = []

        if "actions" in config:
            actions = config["actions"]
            if not isinstance(actions, dict):
                errors.append(
                    ValidationError(
                        f"Section 'actions' must be a dictionary, got {type(actions).__name__}",
                        field="actions",
                        value=actions,
                    ),
                )

        return errors

    @staticmethod
    def load_and_validate(path: str | Path) -> dict[str, Any]:
        """Load and validate configuration in one step.

        Args:
            path: Path to the YAML configuration file

        Returns:
            Validated configuration dictionary

        Raises:
            ConfigurationError: If file cannot be loaded
            ConfigurationError: If validation fails (first error only)
        """
        config = ConfigLoader.load(path)
        errors = ConfigLoader.validate(config)

        if errors:
            # Raise first error with context
            first_error = errors[0]
            raise ConfigurationError(
                f"Configuration validation failed: {first_error.message}",
                context={
                    "path": str(path),
                    "total_errors": len(errors),
                    "errors": [str(e) for e in errors],
                },
            )

        return config

    @staticmethod
    def load_validated(path: str | Path) -> "SoniConfig":
        """Load and validate configuration using Pydantic models.

        Args:
            path: Path to the YAML configuration file

        Returns:
            Validated SoniConfig instance

        Raises:
            ConfigurationError: If file cannot be loaded
            pydantic.ValidationError: If validation fails
        """
        return SoniConfig.from_yaml(path)


class ModelConfig(BaseModel):
    """Configuration for a language model."""

    provider: str = Field(..., description="Model provider (e.g., 'openai')")
    model: str = Field(..., description="Model name (e.g., 'gpt-4o-mini')")
    temperature: float = Field(
        default=0.1,
        ge=0.0,
        le=2.0,
        description="Temperature for generation",
    )


class NLUModelConfig(ModelConfig):
    """Configuration for NLU model."""

    use_reasoning: bool = Field(
        default=False,
        description=(
            "If True, use ChainOfThought with explicit reasoning (slower, more precise). "
            "If False, use Predict without reasoning (faster, fewer tokens). Default: False"
        ),
    )


class GenerationModelConfig(ModelConfig):
    """Configuration for generation model."""

    max_tokens: int = Field(
        default=500,
        ge=1,
        description="Maximum tokens to generate",
    )


class ModelsConfig(BaseModel):
    """Configuration for all models."""

    nlu: NLUModelConfig = Field(..., description="NLU model configuration")
    generation: GenerationModelConfig | None = Field(
        default=None,
        description="Generation model configuration (optional in MVP)",
    )


class PersistenceConfig(BaseModel):
    """Configuration for state persistence."""

    backend: str = Field(
        default="sqlite",
        description="Backend type: sqlite, postgresql, redis, memory, none",
    )
    path: str = Field(
        default="./dialogue_state.db",
        description="Path to database file (for sqlite). Ignored for memory backend.",
    )


class LoggingConfig(BaseModel):
    """Configuration for logging."""

    level: str = Field(
        default="INFO",
        description="Logging level: DEBUG, INFO, WARNING, ERROR",
    )
    trace_graphs: bool = Field(
        default=False,
        description="Whether to trace graph execution",
    )


class SecurityConfig(BaseModel):
    """Configuration for security guardrails."""

    enable_guardrails: bool = Field(
        default=True,
        description="Whether to enable security guardrails",
    )
    allowed_actions: list[str] = Field(
        default_factory=list,
        description="List of allowed actions. Empty list means all actions are allowed.",
    )
    blocked_intents: list[str] = Field(
        default_factory=list,
        description="List of blocked intents",
    )
    max_confidence_threshold: float = Field(
        default=0.95,
        ge=0.0,
        le=1.0,
        description="Maximum confidence threshold (0.0 to 1.0)",
    )
    min_confidence_threshold: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Minimum confidence threshold (0.0 to 1.0)",
    )


class Settings(BaseModel):
    """Global settings configuration."""

    models: ModelsConfig = Field(..., description="Model configurations")
    persistence: PersistenceConfig = Field(
        default_factory=PersistenceConfig,
        description="Persistence configuration",
    )
    logging: LoggingConfig = Field(
        default_factory=LoggingConfig,
        description="Logging configuration",
    )
    security: SecurityConfig = Field(
        default_factory=SecurityConfig,
        description="Security configuration",
    )


class StepConfig(BaseModel):
    """Configuration for a single step in a flow."""

    step: str = Field(..., description="Step identifier")
    type: str = Field(..., description="Step type: collect, action, branch, confirm, while, say")
    slot: str | None = Field(
        default=None,
        description="Slot name (for collect steps)",
    )
    call: str | None = Field(
        default=None,
        description="Action name (for action steps)",
    )
    map_outputs: dict[str, str] | None = Field(
        default=None,
        description="Output mapping (for action steps)",
    )
    input: str | None = Field(
        default=None,
        description="State variable to evaluate (for branch steps)",
    )
    cases: dict[str, str] | None = Field(
        default=None,
        description="Case mapping: case_value -> target (for branch steps)",
    )
    jump_to: str | None = Field(
        default=None,
        description="Explicit jump to another step (breaks sequential flow)",
    )
    message: str | None = Field(
        default=None,
        description="Message to display (for confirm/say steps, supports {slot} interpolation)",
    )
    # While loop fields
    condition: str | None = Field(
        default=None,
        description="Condition expression for while loops (e.g., 'not confirmed', 'retries < 3')",
    )
    do: list[str] | None = Field(
        default=None,
        description="List of step names to execute in the loop body (for while steps)",
    )


class TriggerConfig(BaseModel):
    """Configuration for flow trigger."""

    intents: list[str] = Field(
        default_factory=list,
        description=(
            "List of natural language phrase examples that trigger this flow. "
            "Used for NLU optimization - the LLM learns to map these phrases to the flow name. "
            'Example: ["I want to book a flight", "Book me a flight"]'
        ),
    )


class FlowConfig(BaseModel):
    """Configuration for a dialogue flow."""

    description: str = Field(..., description="Flow description")
    trigger: TriggerConfig | None = Field(
        default=None, description="Flow trigger configuration (intents that activate this flow)"
    )
    steps: list[StepConfig] | None = Field(
        default=None, description="List of steps in the flow (legacy format)"
    )
    process: list[StepConfig] | None = Field(
        default=None, description="List of steps in the flow (procedural DSL format)"
    )

    def model_post_init(self, __context: Any) -> None:
        """Validate that either steps or process is provided."""
        if self.steps is None and self.process is None:
            raise ValueError("FlowConfig must have either 'steps' or 'process' field")
        if self.steps is not None and self.process is not None:
            raise ValueError("FlowConfig cannot have both 'steps' and 'process' fields")

    @property
    def steps_or_process(self) -> list[StepConfig]:
        """Get steps or process, whichever is available."""
        if self.process is not None:
            return self.process
        if self.steps is not None:
            return self.steps
        raise ValueError("FlowConfig must have either 'steps' or 'process' field")


class SlotConfig(BaseModel):
    """Configuration for a slot/entity."""

    type: str = Field(..., description="Slot type: string, number, date, etc.")
    prompt: str = Field(..., description="Prompt to ask user for this slot")
    required: bool = Field(
        default=True,
        description="Whether slot is required",
    )
    validator: str | None = Field(
        default=None,
        description="Validator name (optional in MVP)",
    )


class ActionConfig(BaseModel):
    """Configuration for an action.

    Actions must be registered in Python using ActionRegistry.register().
    """

    description: str | None = Field(
        default=None,
        description="Action description",
    )
    inputs: list[str] = Field(
        default_factory=list,
        description="List of input slot names",
    )
    outputs: list[str] = Field(
        default_factory=list,
        description="List of output variable names",
    )


class SoniConfig(BaseModel):
    """Root configuration model for Soni Framework."""

    version: str = Field(..., description="Configuration version")
    settings: Settings = Field(..., description="Global settings")
    flows: dict[str, FlowConfig] = Field(
        default_factory=dict,
        description="Dialogue flows",
    )
    slots: dict[str, SlotConfig] = Field(
        default_factory=dict,
        description="Slot definitions",
    )
    actions: dict[str, ActionConfig] = Field(
        default_factory=dict,
        description="Action definitions",
    )

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "SoniConfig":
        """Create SoniConfig from a dictionary.

        Args:
            data: Configuration dictionary

        Returns:
            Validated SoniConfig instance

        Raises:
            pydantic.ValidationError: If validation fails
        """
        return cls(**data)

    @classmethod
    def from_yaml(cls, path: str | Path) -> "SoniConfig":
        """Load and validate configuration from YAML file.

        Args:
            path: Path to YAML configuration file

        Returns:
            Validated SoniConfig instance

        Raises:
            ConfigurationError: If file cannot be loaded
            pydantic.ValidationError: If validation fails
        """
        raw_config = ConfigLoader.load(path)
        return cls.from_dict(raw_config)
