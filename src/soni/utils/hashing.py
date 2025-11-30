"""Hashing utilities for cache keys and identifiers"""

import hashlib
import json
from typing import Any


def generate_cache_key(*parts: str | int | float) -> str:
    """
    Generate MD5 cache key from parts.

    Args:
        *parts: String/numeric parts to hash together

    Returns:
        32-character hexadecimal MD5 hash

    Example:
        >>> generate_cache_key("user123", "booking", "origin,destination")
        'a1b2c3d4e5f6...'
    """
    content = ":".join(str(p) for p in parts)
    return hashlib.md5(content.encode()).hexdigest()


def generate_cache_key_from_dict(data: dict[str, Any], sort_keys: bool = True) -> str:
    """
    Generate MD5 cache key from dictionary.

    Args:
        data: Dictionary to hash
        sort_keys: Whether to sort keys for consistent hashing (default: True)

    Returns:
        32-character hexadecimal MD5 hash

    Example:
        >>> generate_cache_key_from_dict({"flow": "booking", "slots": {"origin": "NYC"}})
        'a1b2c3d4e5f6...'
    """
    key_data = json.dumps(data, sort_keys=sort_keys)
    return hashlib.md5(key_data.encode()).hexdigest()
