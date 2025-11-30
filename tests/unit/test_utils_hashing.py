"""Tests for hashing utilities"""

from soni.utils.hashing import generate_cache_key, generate_cache_key_from_dict


def test_generate_cache_key_consistent():
    """Test cache key generation is consistent"""
    # Arrange & Act
    key1 = generate_cache_key("a", "b", "c")
    key2 = generate_cache_key("a", "b", "c")

    # Assert
    assert key1 == key2
    assert len(key1) == 32  # MD5 hex length


def test_generate_cache_key_different_for_different_inputs():
    """Test different inputs produce different keys"""
    # Arrange & Act
    key1 = generate_cache_key("a", "b", "c")
    key2 = generate_cache_key("a", "b", "d")

    # Assert
    assert key1 != key2


def test_generate_cache_key_handles_numbers():
    """Test cache key handles numeric inputs"""
    # Arrange & Act
    key = generate_cache_key("user", 123, 45.6)

    # Assert
    assert len(key) == 32  # MD5 hex length
    assert isinstance(key, str)


def test_generate_cache_key_from_dict_consistent():
    """Test cache key from dict is consistent"""
    # Arrange
    data = {"flow": "booking", "slots": {"origin": "NYC"}}

    # Act
    key1 = generate_cache_key_from_dict(data)
    key2 = generate_cache_key_from_dict(data)

    # Assert
    assert key1 == key2
    assert len(key1) == 32


def test_generate_cache_key_from_dict_different_for_different_inputs():
    """Test different dicts produce different keys"""
    # Arrange
    data1 = {"flow": "booking", "slots": {"origin": "NYC"}}
    data2 = {"flow": "booking", "slots": {"origin": "LAX"}}

    # Act
    key1 = generate_cache_key_from_dict(data1)
    key2 = generate_cache_key_from_dict(data2)

    # Assert
    assert key1 != key2


def test_generate_cache_key_from_dict_sorts_keys():
    """Test cache key from dict sorts keys for consistency"""
    # Arrange
    data1 = {"b": 2, "a": 1}
    data2 = {"a": 1, "b": 2}

    # Act
    key1 = generate_cache_key_from_dict(data1, sort_keys=True)
    key2 = generate_cache_key_from_dict(data2, sort_keys=True)

    # Assert
    assert key1 == key2


def test_generate_cache_key_from_dict_without_sorting():
    """Test cache key from dict without sorting produces different keys"""
    # Arrange
    data1 = {"b": 2, "a": 1}
    data2 = {"a": 1, "b": 2}

    # Act
    key1 = generate_cache_key_from_dict(data1, sort_keys=False)
    key2 = generate_cache_key_from_dict(data2, sort_keys=False)

    # Assert
    # Without sorting, order matters, so keys should be different
    assert key1 != key2
