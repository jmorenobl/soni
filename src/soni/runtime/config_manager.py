"""Configuration management for runtime"""

from pathlib import Path

from pydantic import ValidationError

from soni.core.config import ConfigLoader, SoniConfig
from soni.core.errors import ConfigurationError


class ConfigurationManager:
    """Manages configuration loading and validation."""

    def __init__(self, config_path: str | Path):
        """
        Initialize ConfigurationManager.

        Args:
            config_path: Path to YAML configuration file
        """
        self.config_path = Path(config_path)
        self.config: SoniConfig | None = None

    def load(self) -> SoniConfig:
        """
        Load and validate configuration.

        Returns:
            Validated SoniConfig instance

        Raises:
            ConfigurationError: If configuration cannot be loaded or validated
        """
        try:
            config_dict = ConfigLoader.load(self.config_path)
            self.config = SoniConfig(**config_dict)
            return self.config
        except ValidationError as e:
            raise ConfigurationError(
                f"Invalid configuration schema: {e}",
                context={"config_path": str(self.config_path)},
            ) from e
