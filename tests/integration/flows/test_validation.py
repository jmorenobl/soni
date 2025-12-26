import pytest

from soni.config.loader import ConfigLoader
from soni.config.models import SoniConfig
from soni.core.validation import validate_flow_definition


class TestIntegrationValidation:
    """Integration tests for configuration validation."""

    def test_validate_banking_domain(self):
        """Should validate all flows in the banking example."""
        # Load real config
        from pathlib import Path

        config_path = Path("examples/banking/domain")
        if not config_path.exists():
            pytest.skip("Banking example not found")

        config = ConfigLoader.load(config_path)
        assert isinstance(config, SoniConfig)

        # Convert to dict and validate each flow using core/validation
        config_dict = config.model_dump()
        for flow_name, flow_data in config_dict["flows"].items():
            # Add name back if missing in dump
            flow_data["name"] = flow_name
            validate_flow_definition(flow_data)

    def test_validate_ecommerce_domain(self):
        """Should validate all flows in the ecommerce example."""
        from pathlib import Path

        config_path = Path("examples/ecommerce/domain")
        if not config_path.exists():
            # Some environments might not have all examples
            pytest.skip("Ecommerce example not found")

        config = ConfigLoader.load(config_path)
        config_dict = config.model_dump()
        for flow_name, flow_data in config_dict["flows"].items():
            flow_data["name"] = flow_name
            validate_flow_definition(flow_data)
