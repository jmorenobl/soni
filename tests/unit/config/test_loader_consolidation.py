"""Tests for config loader consolidation.

Verifies that ConfigLoader is accessible from canonical location only.
"""

import pytest


class TestConfigLoaderImports:
    """Tests for consolidated ConfigLoader imports."""

    def test_import_from_config_loader(self):
        """Test that ConfigLoader can be imported from soni.config.loader."""
        from soni.config.loader import ConfigLoader

        assert ConfigLoader is not None
        assert hasattr(ConfigLoader, "load")

    def test_import_from_config_package(self):
        """Test that ConfigLoader can be imported from soni.config."""
        from soni.config import ConfigLoader

        assert ConfigLoader is not None

    def test_core_loader_removed(self):
        """Test that soni.core.loader no longer exists."""
        with pytest.raises(ImportError, match="No module named 'soni.core.loader'"):
            import importlib

            importlib.import_module("soni.core.loader")

    def test_core_config_removed(self):
        """Test that soni.core.config no longer exists."""
        with pytest.raises(ImportError, match="No module named 'soni.core.config'"):
            import importlib

            importlib.import_module("soni.core.config")


class TestConfigLoaderFunctionality:
    """Tests that ConfigLoader works correctly after consolidation."""

    def test_load_from_file(self, tmp_path):
        """Test loading config from YAML file."""
        from soni.config.loader import ConfigLoader

        config_file = tmp_path / "soni.yaml"
        config_file.write_text("""
settings:
  models:
    provider: openai
    model: gpt-4
flows:
  greeting:
    name: greeting
    description: A greeting flow
    steps:
      - step: greet
        type: say
        message: Hello!
""")

        config = ConfigLoader.load(config_file)

        assert config is not None
        assert "greeting" in config.flows

    def test_load_from_directory(self, tmp_path):
        """Test loading config from directory with multiple YAML files."""
        from soni.config.loader import ConfigLoader

        # Create multiple YAML files
        (tmp_path / "settings.yaml").write_text("""
settings:
  models:
    nlu:
      provider: openai
      model: gpt-4
""")

        (tmp_path / "flows.yaml").write_text("""
flows:
  greeting:
    name: greeting
    description: Test
    steps:
      - step: greet
        type: say
        message: Hello!
""")

        config = ConfigLoader.load(tmp_path)

        assert config is not None
        assert config.settings.models.nlu.model == "gpt-4"
        assert "greeting" in config.flows
