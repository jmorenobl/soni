"""Validation module for Soni Framework"""

# Import validators to auto-register them
from soni.validation import validators  # noqa: F401
from soni.validation.registry import ValidatorRegistry

__all__ = ["ValidatorRegistry"]
