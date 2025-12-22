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

        data: dict[str, Any] = {"flows": {}, "settings": {}}

        # Handle directory
        if config_path.is_dir():
            yaml_file = config_path / "soni.yaml"
            if not yaml_file.exists():
                yaml_file = config_path / "config.yaml"

            # If explicit master file exists, use it
            if yaml_file.exists():
                with open(yaml_file, encoding="utf-8") as f:
                    data = yaml.safe_load(f) or {}
            else:
                # Merge all .yaml files in directory
                files = sorted(config_path.glob("*.yaml"))
                if not files:
                    raise FileNotFoundError(f"No config files found in {config_path}")

                for fpath in files:
                    with open(fpath, encoding="utf-8") as f:
                        chunk = yaml.safe_load(f) or {}

                        # Merge flows
                        if "flows" in chunk and isinstance(chunk["flows"], dict):
                            data["flows"].update(chunk["flows"])

                        # Merge settings
                        if "settings" in chunk and isinstance(chunk["settings"], dict):
                            data["settings"].update(chunk["settings"])

                        # Overwrite other top-level keys (e.g. version)
                        for k, v in chunk.items():
                            if k not in ("flows", "settings"):
                                data[k] = v

        else:
            # Handle single file
            yaml_file = config_path
            if not yaml_file.exists():
                raise FileNotFoundError(f"Config file not found: {yaml_file}")

            with open(yaml_file, encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}

        # Pydantic's model_validate returns Self, but mypy infers Any
        return SoniConfig.model_validate(data)  # type: ignore[no-any-return]
