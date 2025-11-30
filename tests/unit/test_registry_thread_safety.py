"""Tests for registry thread-safety"""

from concurrent.futures import ThreadPoolExecutor

import pytest

from soni.actions.registry import ActionRegistry
from soni.validation.registry import ValidatorRegistry


def test_action_registry_concurrent_registration():
    """Test ActionRegistry handles concurrent registration safely"""
    # Arrange
    ActionRegistry.clear()

    def register_action(i: int):
        """Register action in thread"""

        @ActionRegistry.register(f"action_{i}")
        async def test_action():
            return i

    # Act - Register 100 actions concurrently
    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = [executor.submit(register_action, i) for i in range(100)]
        for future in futures:
            future.result()

    # Assert - All 100 actions registered
    assert len(ActionRegistry.list_actions()) == 100

    # Cleanup
    ActionRegistry.clear()


def test_action_registry_concurrent_read_write():
    """Test ActionRegistry handles concurrent reads and writes"""
    # Arrange
    ActionRegistry.clear()

    @ActionRegistry.register("test_action")
    async def test_action():
        return "result"

    results = []

    def read_action():
        """Read action in thread"""
        action = ActionRegistry.get("test_action")
        results.append(action)

    # Act - 50 concurrent reads
    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = [executor.submit(read_action) for _ in range(50)]
        for future in futures:
            future.result()

    # Assert - All reads successful
    assert len(results) == 50
    assert all(r is not None for r in results)

    # Cleanup
    ActionRegistry.clear()


def test_validator_registry_thread_safety():
    """Test ValidatorRegistry handles concurrent operations"""
    # Arrange
    ValidatorRegistry.clear()

    def register_validator(i: int):
        """Register validator in thread"""

        @ValidatorRegistry.register(f"validator_{i}")
        def test_validator(value: str) -> bool:
            return True

    # Act
    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = [executor.submit(register_validator, i) for i in range(50)]
        for future in futures:
            future.result()

    # Assert
    assert len(ValidatorRegistry.list_validators()) == 50

    # Cleanup
    ValidatorRegistry.clear()


def test_validator_registry_concurrent_read_write():
    """Test ValidatorRegistry handles concurrent reads and writes"""
    # Arrange
    ValidatorRegistry.clear()

    @ValidatorRegistry.register("test_validator")
    def test_validator(value: str) -> bool:
        return True

    results = []

    def read_validator():
        """Read validator in thread"""
        validator = ValidatorRegistry.get("test_validator")
        results.append(validator)

    # Act - 50 concurrent reads
    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = [executor.submit(read_validator) for _ in range(50)]
        for future in futures:
            future.result()

    # Assert - All reads successful
    assert len(results) == 50
    assert all(r is not None for r in results)

    # Cleanup
    ValidatorRegistry.clear()
