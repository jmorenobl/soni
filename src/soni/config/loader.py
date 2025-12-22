"""Config loader for YAML configuration files."""

from pathlib import Path
from typing import Any

import yaml

from soni.config.models import SoniConfig


class ConfigLoader:
    """Load SoniConfig from YAML files."""

    @staticmethod
    def load(path: Path | str) -> SoniConfig:
        """Load configuration from YAML file.

        Args:
            path: Path to config directory or soni.yaml file

        Returns:
            Parsed SoniConfig instance
        """
        config_path = Path(path)

        # Handle directory or file
        if config_path.is_dir():
            yaml_file = config_path / "soni.yaml"
            if not yaml_file.exists():
                yaml_file = config_path / "config.yaml"
        else:
            yaml_file = config_path

        if not yaml_file.exists():
            raise FileNotFoundError(f"Config file not found: {yaml_file}")

        with open(yaml_file, encoding="utf-8") as f:
            data: dict[str, Any] = yaml.safe_load(f) or {}

        # Pydantic's model_validate returns Self, but mypy infers Any
        return SoniConfig.model_validate(data)  # type: ignore[no-any-return]
