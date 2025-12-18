"""Configuration loader.

Handles loading and merging YAML configuration files.
"""

from pathlib import Path
from typing import TYPE_CHECKING

import yaml

if TYPE_CHECKING:
    from soni.config.main import SoniConfig


class ConfigLoader:
    """Loader for Soni configuration files.

    Supports both single YAML files and directories containing multiple YAML files.
    When loading from a directory, all .yaml/.yml files are merged in alphabetical order.
    """

    @staticmethod
    def load(path: str | Path) -> "SoniConfig":
        """Load and validate configuration from YAML file or directory.

        Args:
            path: Path to YAML configuration file or directory containing YAML files.

        Returns:
            Validated SoniConfig object.

        Raises:
            ConfigError: If file/directory not found or invalid format.
        """
        # Import here to avoid circular dependency
        from soni.config.main import SoniConfig
        from soni.core.errors import ConfigError

        path = Path(path)
        if not path.exists():
            raise ConfigError(f"Configuration file not found: {path}")

        try:
            if path.is_dir():
                data = ConfigLoader._load_directory(path)
            else:
                data = ConfigLoader._load_file(path)

            return SoniConfig(**data)
        except yaml.YAMLError as e:
            raise ConfigError(f"Error parsing YAML: {e}") from e
        except Exception as e:
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
        from soni.core.errors import ConfigError

        merged: dict = {}
        yaml_files = sorted(directory.glob("*.yaml")) + sorted(directory.glob("*.yml"))

        if not yaml_files:
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
