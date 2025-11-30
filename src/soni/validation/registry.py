"""Thread-safe registry for slot validators"""

import logging
from collections.abc import Callable
from threading import Lock
from typing import Any

logger = logging.getLogger(__name__)

# Estado global con lock para thread-safety
_validators: dict[str, Callable[[Any], bool]] = {}
_validators_lock = Lock()


class ValidatorRegistry:
    """
    Thread-safe registry for slot validators.

    All mutations are protected by a lock to ensure thread-safety
    in concurrent environments.
    """

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
            with _validators_lock:  # Thread-safe mutation
                if name in _validators:
                    logger.warning(
                        f"Validator '{name}' already registered, overwriting",
                        extra={"validator_name": name},
                    )
                _validators[name] = func
                logger.debug(
                    f"Registered validator '{name}'",
                    extra={"validator_name": name},
                )
            return func

        return decorator

    @classmethod
    def get(cls, name: str) -> Callable[[Any], bool]:
        """
        Get validator by name (thread-safe read).

        Args:
            name: Validator name

        Returns:
            Validator function

        Raises:
            ValueError: If validator is not registered
        """
        with _validators_lock:  # Thread-safe read
            if name not in _validators:
                raise ValueError(
                    f"Validator '{name}' not registered. Available: {list(_validators.keys())}"
                )
            return _validators[name]

    @classmethod
    def validate(cls, name: str, value: Any) -> bool:
        """
        Validate value using named validator (thread-safe).

        Args:
            name: Validator name
            value: Value to validate

        Returns:
            True if valid, False otherwise

        Raises:
            ValueError: If validator is not registered
        """
        validator = cls.get(name)  # get() is already thread-safe
        return validator(value)

    @classmethod
    def list_validators(cls) -> list[str]:
        """
        List all registered validator names (thread-safe).

        Returns:
            List of validator names
        """
        with _validators_lock:  # Thread-safe read
            return list(_validators.keys())

    @classmethod
    def is_registered(cls, name: str) -> bool:
        """
        Check if validator is registered (thread-safe).

        Args:
            name: Validator name

        Returns:
            True if registered, False otherwise
        """
        with _validators_lock:  # Thread-safe read
            return name in _validators

    @classmethod
    def clear(cls) -> None:
        """
        Clear all registered validators (thread-safe).

        Warning: This is primarily for testing. Use with caution.
        """
        with _validators_lock:  # Thread-safe mutation
            count = len(_validators)
            _validators.clear()
            logger.debug(
                f"Cleared {count} registered validator(s)",
                extra={"count": count},
            )
