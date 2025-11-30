"""Configuration management for runtime"""

from pathlib import Path

from soni.core.config import ConfigLoader, SoniConfig


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
        config_dict = ConfigLoader.load(self.config_path)
        self.config = SoniConfig(**config_dict)
        return self.config
