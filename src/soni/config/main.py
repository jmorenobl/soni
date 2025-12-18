"""Main SoniConfig model.

The root configuration model that aggregates all configuration sections.
"""

from pathlib import Path

from pydantic import BaseModel, Field

from soni.config.models import FlowConfig, SlotConfig
from soni.config.settings import SettingsConfig


class SoniConfig(BaseModel):
    """Main configuration model."""

    version: str = "1.0"
    settings: SettingsConfig = Field(default_factory=SettingsConfig)
    slots: dict[str, SlotConfig] = Field(default_factory=dict)
    flows: dict[str, FlowConfig] = Field(default_factory=dict)

    @classmethod
    def from_yaml(cls, path: str | Path) -> "SoniConfig":
        """Load configuration from YAML file."""
        from soni.config.loader import ConfigLoader

        return ConfigLoader.load(path)
