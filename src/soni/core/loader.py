"""Configuration loader service."""
from pathlib import Path

import yaml

from soni.core.config import SoniConfig
from soni.core.errors import ConfigError


class ConfigLoader:
    """Loads configuration from various sources."""

    @staticmethod
    def from_yaml(path: Path) -> SoniConfig:
        """Load from YAML file.

        Args:
            path: Path to YAML config file.
        Returns:
            SoniConfig object.

        Raises:
            ConfigError: If file not found or parsing fails.
        """
        if not path.exists():
            raise ConfigError(f"Config not found: {path}")

        try:
            with open(path) as f:
                data = yaml.safe_load(f)
            return SoniConfig.model_validate(data)
        except Exception as e:
            raise ConfigError(f"Failed to load config: {e}") from e
