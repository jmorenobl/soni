"""Tests for dataset constants module."""

from soni.dataset.constants import (
    DEFAULT_EXAMPLE_DATETIME,
    SHARED_CONFIRMATION_NEGATIVE,
    SHARED_CONFIRMATION_POSITIVE,
    SHARED_CONFIRMATION_UNCLEAR,
)


class TestConstants:
    """Tests for dataset constants."""

    def test_default_datetime_is_string(self):
        """Test DEFAULT_EXAMPLE_DATETIME is a valid string."""
        assert isinstance(DEFAULT_EXAMPLE_DATETIME, str)
        assert len(DEFAULT_EXAMPLE_DATETIME) > 0

    def test_confirmation_positive_is_list(self):
        """Test positive confirmations are a non-empty list."""
        assert isinstance(SHARED_CONFIRMATION_POSITIVE, list)
        assert len(SHARED_CONFIRMATION_POSITIVE) > 0

    def test_confirmation_negative_is_list(self):
        """Test negative confirmations are a non-empty list."""
        assert isinstance(SHARED_CONFIRMATION_NEGATIVE, list)
        assert len(SHARED_CONFIRMATION_NEGATIVE) > 0

    def test_confirmation_unclear_is_list(self):
        """Test unclear confirmations are a non-empty list."""
        assert isinstance(SHARED_CONFIRMATION_UNCLEAR, list)
        assert len(SHARED_CONFIRMATION_UNCLEAR) > 0
