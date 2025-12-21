import pytest

from soni.core.constants import get_flow_node_name


class TestGetFlowNodeName:
    """Tests for flow node naming helper."""

    def test_generates_correct_prefix(self):
        """Test that node name has flow_ prefix."""
        # Arrange
        flow_name = "book_flight"

        # Act
        result = get_flow_node_name(flow_name)

        # Assert
        assert result == "flow_book_flight"

    def test_handles_underscore_in_name(self):
        """Test names with underscores work correctly."""
        # Arrange
        flow_name = "transfer_funds"

        # Act
        result = get_flow_node_name(flow_name)

        # Assert
        assert result == "flow_transfer_funds"

    def test_consistent_with_builder(self):
        """Test that result matches pattern used in builder."""
        # Arrange
        flow_name = "test_flow"

        # Act
        helper_result = get_flow_node_name(flow_name)
        manual_result = f"flow_{flow_name}"

        # Assert
        assert helper_result == manual_result
