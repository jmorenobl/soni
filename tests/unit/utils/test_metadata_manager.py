"""Tests for MetadataManager utility."""

import pytest

from soni.utils.metadata_manager import MetadataManager


class TestClearConfirmationFlags:
    """Tests for clearing confirmation flags."""

    def test_clears_all_confirmation_flags(self):
        """Test that all confirmation flags are removed."""
        # Arrange
        metadata = {
            "_confirmation_attempts": 2,
            "_confirmation_processed": True,
            "_confirmation_unclear": True,
            "other_key": "should_remain",
        }

        # Act
        result = MetadataManager.clear_confirmation_flags(metadata)

        # Assert
        assert "_confirmation_attempts" not in result
        assert "_confirmation_processed" not in result
        assert "_confirmation_unclear" not in result
        assert result["other_key"] == "should_remain"

    def test_handles_missing_flags_gracefully(self):
        """Test clearing when flags don't exist."""
        # Arrange
        metadata = {"other_key": "value"}

        # Act
        result = MetadataManager.clear_confirmation_flags(metadata)

        # Assert - should not raise error
        assert result == {"other_key": "value"}

    def test_returns_new_dict_immutable(self):
        """Test that original metadata is not modified (immutable)."""
        # Arrange
        metadata = {"_confirmation_attempts": 2}

        # Act
        result = MetadataManager.clear_confirmation_flags(metadata)

        # Assert
        assert metadata["_confirmation_attempts"] == 2  # Original unchanged
        assert "_confirmation_attempts" not in result  # New dict cleared


class TestClearCorrectionFlags:
    """Tests for clearing correction flags."""

    def test_clears_correction_flags(self):
        """Test that correction flags are removed."""
        # Arrange
        metadata = {
            "_correction_slot": "origin",
            "_correction_value": "NYC",
            "other_key": "remains",
        }

        # Act
        result = MetadataManager.clear_correction_flags(metadata)

        # Assert
        assert "_correction_slot" not in result
        assert "_correction_value" not in result
        assert result["other_key"] == "remains"


class TestClearModificationFlags:
    """Tests for clearing modification flags."""

    def test_clears_modification_flags(self):
        """Test that modification flags are removed."""
        # Arrange
        metadata = {
            "_modification_slot": "destination",
            "_modification_value": "LAX",
            "other_key": "remains",
        }

        # Act
        result = MetadataManager.clear_modification_flags(metadata)

        # Assert
        assert "_modification_slot" not in result
        assert "_modification_value" not in result
        assert result["other_key"] == "remains"


class TestClearAllFlowFlags:
    """Tests for clearing all flow flags."""

    def test_clears_all_flow_flags(self):
        """Test that all flow-related flags are removed."""
        # Arrange
        metadata = {
            "_confirmation_attempts": 2,
            "_confirmation_processed": True,
            "_confirmation_unclear": False,
            "_correction_slot": "origin",
            "_correction_value": "NYC",
            "_modification_slot": "destination",
            "_modification_value": "LAX",
            "other_key": "should_remain",
        }

        # Act
        result = MetadataManager.clear_all_flow_flags(metadata)

        # Assert
        # All flow flags removed
        assert "_confirmation_attempts" not in result
        assert "_confirmation_processed" not in result
        assert "_confirmation_unclear" not in result
        assert "_correction_slot" not in result
        assert "_correction_value" not in result
        assert "_modification_slot" not in result
        assert "_modification_value" not in result
        # Other keys remain
        assert result["other_key"] == "should_remain"


class TestSetCorrectionFlags:
    """Tests for setting correction flags."""

    def test_sets_correction_flags(self):
        """Test that correction flags are set correctly."""
        # Arrange
        metadata = {}

        # Act
        result = MetadataManager.set_correction_flags(metadata, "origin", "NYC")

        # Assert
        assert result["_correction_slot"] == "origin"
        assert result["_correction_value"] == "NYC"

    def test_clears_modification_flags_when_setting_correction(self):
        """Test that modification flags are cleared when setting correction."""
        # Arrange
        metadata = {
            "_modification_slot": "destination",
            "_modification_value": "LAX",
        }

        # Act
        result = MetadataManager.set_correction_flags(metadata, "origin", "NYC")

        # Assert
        assert result["_correction_slot"] == "origin"
        assert result["_correction_value"] == "NYC"
        assert "_modification_slot" not in result
        assert "_modification_value" not in result


class TestSetModificationFlags:
    """Tests for setting modification flags."""

    def test_sets_modification_flags(self):
        """Test that modification flags are set correctly."""
        # Arrange
        metadata = {}

        # Act
        result = MetadataManager.set_modification_flags(metadata, "destination", "LAX")

        # Assert
        assert result["_modification_slot"] == "destination"
        assert result["_modification_value"] == "LAX"

    def test_clears_correction_flags_when_setting_modification(self):
        """Test that correction flags are cleared when setting modification."""
        # Arrange
        metadata = {
            "_correction_slot": "origin",
            "_correction_value": "NYC",
        }

        # Act
        result = MetadataManager.set_modification_flags(metadata, "destination", "LAX")

        # Assert
        assert result["_modification_slot"] == "destination"
        assert result["_modification_value"] == "LAX"
        assert "_correction_slot" not in result
        assert "_correction_value" not in result


class TestConfirmationAttempts:
    """Tests for confirmation attempts counter."""

    def test_increment_confirmation_attempts(self):
        """Test incrementing confirmation attempts."""
        # Arrange
        metadata = {"_confirmation_attempts": 1}

        # Act
        result = MetadataManager.increment_confirmation_attempts(metadata)

        # Assert
        assert result["_confirmation_attempts"] == 2

    def test_increment_from_zero(self):
        """Test incrementing when no attempts exist."""
        # Arrange
        metadata = {}

        # Act
        result = MetadataManager.increment_confirmation_attempts(metadata)

        # Assert
        assert result["_confirmation_attempts"] == 1

    def test_get_confirmation_attempts_existing(self):
        """Test getting existing confirmation attempts."""
        # Arrange
        metadata = {"_confirmation_attempts": 3}

        # Act
        result = MetadataManager.get_confirmation_attempts(metadata)

        # Assert
        assert result == 3

    def test_get_confirmation_attempts_default(self):
        """Test getting confirmation attempts returns 0 if not set."""
        # Arrange
        metadata = {}

        # Act
        result = MetadataManager.get_confirmation_attempts(metadata)

        # Assert
        assert result == 0
