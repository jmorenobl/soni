"""Registry for slot validators"""

from collections.abc import Callable
from typing import Any


class ValidatorRegistry:
    """Registry for slot validators."""

    _validators: dict[str, Callable[[Any], bool]] = {}

    @classmethod
    def register(cls, name: str) -> Callable:
        """
        Register a validator function.

        Usage:
            @ValidatorRegistry.register("city_name")
            def validate_city(value: str) -> bool:
                return value.isalpha() and len(value) > 1

        Args:
            name: Semantic name for the validator

        Returns:
            Decorator function
        """

        def decorator(func: Callable[[Any], bool]) -> Callable[[Any], bool]:
            cls._validators[name] = func
            return func

        return decorator

    @classmethod
    def get(cls, name: str) -> Callable[[Any], bool]:
        """
        Get validator by name.

        Args:
            name: Validator name

        Returns:
            Validator function

        Raises:
            ValueError: If validator is not registered
        """
        if name not in cls._validators:
            raise ValueError(
                f"Validator '{name}' not registered. Available: {list(cls._validators.keys())}"
            )
        return cls._validators[name]

    @classmethod
    def validate(cls, name: str, value: Any) -> bool:
        """
        Validate value using named validator.

        Args:
            name: Validator name
            value: Value to validate

        Returns:
            True if valid, False otherwise

        Raises:
            ValueError: If validator is not registered
        """
        validator = cls.get(name)
        return validator(value)

    @classmethod
    def list_validators(cls) -> list[str]:
        """
        List all registered validator names.

        Returns:
            List of validator names
        """
        return list(cls._validators.keys())
