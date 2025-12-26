import pytest
import yaml

from soni.config.loader import ConfigLoader


class TestConfigLoaderEdgeCases:
    """Tests for config loader edge cases."""

    def test_load_nonexistent_directory_fails(self):
        """Loading config from nonexistent directory should fail."""
        with pytest.raises(FileNotFoundError):
            ConfigLoader.load("nonexistent_path")

    def test_load_empty_directory_fails(self, tmp_path):
        """Loading from empty directory should raise FileNotFoundError."""
        domain_dir = tmp_path / "empty_domain"
        domain_dir.mkdir()

        with pytest.raises(FileNotFoundError, match="No config files found"):
            ConfigLoader.load(str(domain_dir))

    def test_load_invalid_yaml_fails(self, tmp_path):
        """Loading invalid YAML files should fail."""
        domain_dir = tmp_path / "invalid_domain"
        domain_dir.mkdir()
        flow_file = domain_dir / "soni.yaml"
        flow_file.write_text("invalid: yaml: architecture: [")

        with pytest.raises(yaml.YAMLError):
            ConfigLoader.load(str(domain_dir))
