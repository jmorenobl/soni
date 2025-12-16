"""Configuration loader service."""

from pathlib import Path

from soni.core.config import ConfigLoader as CoreConfigLoader
from soni.core.config import SoniConfig
from soni.core.errors import ConfigError


class ConfigLoader:
    """Loads configuration from various sources.

    This is a facade that delegates to the core ConfigLoader.
    Supports both single YAML files and directories with multiple YAML files.
    """

    @staticmethod
    def from_yaml(path: Path) -> SoniConfig:
        """Load from YAML file or directory.

        Args:
            path: Path to YAML config file or directory containing YAML files.
        Returns:
            SoniConfig object.

        Raises:
            ConfigError: If file/directory not found or parsing fails.
        """
        if not path.exists():
            raise ConfigError(f"Config not found: {path}")

        return CoreConfigLoader.load(path)
