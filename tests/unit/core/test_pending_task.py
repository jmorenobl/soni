"""Tests for PendingTask types and factories."""

from typing import get_args

import pytest

from soni.core.pending_task import (
    CollectTask,
    ConfirmTask,
    InformTask,
    PendingTask,
    collect,
    confirm,
    inform,
    is_collect,
    is_confirm,
    is_inform,
    requires_input,
)


class TestCollectFactory:
    """Tests for collect() factory function."""

    def test_collect_creates_correct_type(self):
        """Test that collect() creates a CollectTask with correct type literal."""
        # Arrange
        prompt = "What is your account number?"
        slot = "account_number"

        # Act
        task = collect(prompt=prompt, slot=slot)

        # Assert
        assert task["type"] == "collect"
        assert task["prompt"] == prompt
        assert task["slot"] == slot

    def test_collect_with_options(self):
        """Test that collect() includes options when provided."""
        # Arrange
        options = ["checking", "savings"]

        # Act
        task = collect(prompt="Select account", slot="account_type", options=options)

        # Assert
        assert task["options"] == options

    def test_collect_with_metadata(self):
        """Test that collect() includes metadata when provided."""
        # Arrange
        metadata = {"expected_format": "8 digits"}

        # Act
        task = collect(prompt="Enter PIN", slot="pin", metadata=metadata)

        # Assert
        assert task["metadata"] == metadata


class TestConfirmFactory:
    """Tests for confirm() factory function."""

    def test_confirm_creates_correct_type(self):
        """Test that confirm() creates a ConfirmTask with correct type literal."""
        # Arrange
        prompt = "Transfer $500. Proceed?"

        # Act
        task = confirm(prompt=prompt)

        # Assert
        assert task["type"] == "confirm"
        assert task["prompt"] == prompt
        assert task["options"] == ["yes", "no"]  # Default options

    def test_confirm_with_custom_options(self):
        """Test that confirm() uses custom options when provided."""
        # Arrange
        options = ["yes", "no", "cancel"]

        # Act
        task = confirm(prompt="Confirm?", options=options)

        # Assert
        assert task["options"] == options


class TestInformFactory:
    """Tests for inform() factory function."""

    def test_inform_creates_correct_type(self):
        """Test that inform() creates an InformTask with correct type literal."""
        # Arrange
        prompt = "Your balance is $1,234"

        # Act
        task = inform(prompt=prompt)

        # Assert
        assert task["type"] == "inform"
        assert task["prompt"] == prompt
        assert task.get("wait_for_ack") is None  # Default: no wait

    def test_inform_with_wait_for_ack(self):
        """Test that inform() sets wait_for_ack when specified."""
        # Arrange & Act
        task = inform(prompt="Transfer complete!", wait_for_ack=True)

        # Assert
        assert task["wait_for_ack"] is True

    def test_inform_with_options(self):
        """Test that inform() includes options for acknowledgment."""
        # Arrange
        options = ["OK", "Got it"]

        # Act
        task = inform(prompt="Disclaimer", wait_for_ack=True, options=options)

        # Assert
        assert task["options"] == options


class TestTypeGuards:
    """Tests for type guard functions."""

    def test_is_collect_returns_true_for_collect_task(self):
        """Test is_collect() returns True for CollectTask."""
        # Arrange
        task = collect(prompt="Test", slot="test_slot")

        # Act & Assert
        assert is_collect(task) is True
        assert is_confirm(task) is False
        assert is_inform(task) is False

    def test_is_confirm_returns_true_for_confirm_task(self):
        """Test is_confirm() returns True for ConfirmTask."""
        # Arrange
        task = confirm(prompt="Test?")

        # Act & Assert
        assert is_confirm(task) is True
        assert is_collect(task) is False
        assert is_inform(task) is False

    def test_is_inform_returns_true_for_inform_task(self):
        """Test is_inform() returns True for InformTask."""
        # Arrange
        task = inform(prompt="Test")

        # Act & Assert
        assert is_inform(task) is True
        assert is_collect(task) is False
        assert is_confirm(task) is False


class TestRequiresInput:
    """Tests for requires_input() function."""

    def test_collect_requires_input(self):
        """Test that CollectTask always requires input."""
        # Arrange
        task = collect(prompt="Test", slot="slot")

        # Act & Assert
        assert requires_input(task) is True

    def test_confirm_requires_input(self):
        """Test that ConfirmTask always requires input."""
        # Arrange
        task = confirm(prompt="Test?")

        # Act & Assert
        assert requires_input(task) is True

    def test_inform_without_wait_does_not_require_input(self):
        """Test that InformTask without wait_for_ack does not require input."""
        # Arrange
        task = inform(prompt="Test")

        # Act & Assert
        assert requires_input(task) is False

    def test_inform_with_wait_requires_input(self):
        """Test that InformTask with wait_for_ack requires input."""
        # Arrange
        task = inform(prompt="Test", wait_for_ack=True)

        # Act & Assert
        assert requires_input(task) is True
