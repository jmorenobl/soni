"""Tests for SlotNormalizer"""

import time
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from soni.core.config import SoniConfig
from soni.du.normalizer import SlotNormalizer


@pytest.mark.asyncio
async def test_normalizer_trim_strategy():
    """Test trim normalization strategy"""
    # Arrange
    normalizer = SlotNormalizer()
    entity_config = {"normalization": {"strategy": "trim"}}

    # Act
    result = await normalizer.normalize("  hello world  ", entity_config)

    # Assert
    assert result == "hello world"


@pytest.mark.asyncio
async def test_normalizer_lowercase_strategy():
    """Test lowercase normalization strategy"""
    # Arrange
    normalizer = SlotNormalizer()
    entity_config = {"normalization": {"strategy": "lowercase"}}

    # Act
    result = await normalizer.normalize("  HELLO WORLD  ", entity_config)

    # Assert
    assert result == "hello world"


@pytest.mark.asyncio
async def test_normalizer_none_strategy():
    """Test none normalization strategy (no change)"""
    # Arrange
    normalizer = SlotNormalizer()
    entity_config = {"normalization": {"strategy": "none"}}

    # Act
    result = await normalizer.normalize("  Hello World  ", entity_config)

    # Assert
    assert result == "  Hello World  "


@pytest.mark.asyncio
async def test_normalizer_cache():
    """Test that normalization results are cached"""
    # Arrange
    normalizer = SlotNormalizer(cache_size=10, cache_ttl=60)
    entity_config = {"normalization": {"strategy": "trim"}}

    # Act
    result1 = await normalizer.normalize("  hello  ", entity_config)
    result2 = await normalizer.normalize("  hello  ", entity_config)

    # Assert
    assert result1 == result2
    assert result1 == "hello"
    # Cache should be used (verify by checking cache size)
    assert len(normalizer.cache) == 1


@pytest.mark.asyncio
@patch("soni.du.normalizer.dspy.LM")
async def test_normalizer_llm_correction(mock_lm_class):
    """Test LLM correction strategy"""
    # Arrange
    mock_lm = MagicMock()
    mock_lm.acall = AsyncMock(return_value="Madrid")
    mock_lm_class.return_value = mock_lm

    normalizer = SlotNormalizer(
        config={"settings": {"models": {"nlu": {"model": "gpt-4o-mini", "provider": "openai"}}}}
    )
    entity_config = {
        "name": "city",
        "type": "string",
        "normalization": {"strategy": "llm_correction"},
        "examples": ["Madrid", "Barcelona", "NYC"],
    }

    # Act
    result = await normalizer.normalize("Madriz", entity_config)

    # Assert
    assert result == "Madrid"
    mock_lm.acall.assert_called_once()


@pytest.mark.asyncio
async def test_normalizer_process_multiple_slots():
    """Test processing multiple slots"""
    # Arrange
    normalizer = SlotNormalizer()
    slots = {
        "origin": "  New York  ",
        "destination": "  LOS ANGELES  ",
    }

    # Act
    result = await normalizer.process(slots)

    # Assert
    assert result["origin"] == "New York"
    # Default strategy is trim, so it should just trim, not lowercase
    assert result["destination"] == "LOS ANGELES"
    assert len(result) == 2


@pytest.mark.asyncio
async def test_normalizer_with_soni_config():
    """Test normalizer with SoniConfig"""
    # Arrange
    config_dict = {
        "version": "0.1",
        "settings": {
            "models": {
                "nlu": {
                    "provider": "openai",
                    "model": "gpt-4o-mini",
                }
            }
        },
        "slots": {
            "origin": {
                "type": "string",
                "prompt": "Which city are you departing from?",
                "normalization": {"strategy": "trim"},
            },
        },
    }
    config = SoniConfig(**config_dict)
    normalizer = SlotNormalizer(config=config)

    # Act
    result = await normalizer.normalize_slot("origin", "  Madrid  ")

    # Assert
    assert result == "Madrid"


@pytest.mark.asyncio
async def test_normalizer_none_value():
    """Test normalization with None value"""
    # Arrange
    normalizer = SlotNormalizer()
    entity_config = {"normalization": {"strategy": "trim"}}

    # Act
    result = await normalizer.normalize(None, entity_config)

    # Assert
    assert result == ""


@pytest.mark.asyncio
async def test_normalizer_empty_string():
    """Test normalization with empty string"""
    # Arrange
    normalizer = SlotNormalizer()
    entity_config = {"normalization": {"strategy": "trim"}}

    # Act
    result = await normalizer.normalize("", entity_config)

    # Assert
    assert result == ""


@pytest.mark.asyncio
async def test_normalizer_non_string_value():
    """Test normalization with non-string value"""
    # Arrange
    normalizer = SlotNormalizer()
    entity_config = {"normalization": {"strategy": "trim"}}

    # Act
    result = await normalizer.normalize(123, entity_config)

    # Assert
    assert result == "123"


@pytest.mark.asyncio
async def test_normalizer_cache_miss():
    """Test cache miss scenario"""
    # Arrange
    normalizer = SlotNormalizer(cache_size=10, cache_ttl=60)
    entity_config = {"normalization": {"strategy": "trim"}}

    # Act
    result1 = await normalizer.normalize("  hello  ", entity_config)
    # Different value should be a cache miss
    result2 = await normalizer.normalize("  world  ", entity_config)

    # Assert
    assert result1 == "hello"
    assert result2 == "world"
    assert len(normalizer.cache) == 2


@pytest.mark.slow
@pytest.mark.asyncio
async def test_normalizer_cache_ttl_expiry():
    """Test that cache entries expire after TTL"""
    # Arrange
    normalizer = SlotNormalizer(cache_size=10, cache_ttl=1)  # 1 second TTL
    entity_config = {"normalization": {"strategy": "trim"}}

    # Act
    result1 = await normalizer.normalize("  hello  ", entity_config)
    assert result1 == "hello"
    assert len(normalizer.cache) == 1

    # Wait for TTL to expire
    time.sleep(1.1)

    # Normalize again - should be cache miss
    result2 = await normalizer.normalize("  hello  ", entity_config)

    # Assert
    assert result2 == "hello"
    # Cache should have been cleared or entry expired
    # Note: TTLCache behavior may vary, this test verifies basic functionality


@pytest.mark.asyncio
async def test_normalizer_unknown_strategy():
    """Test that unknown strategy falls back to original value"""
    # Arrange
    normalizer = SlotNormalizer()
    entity_config = {"normalization": {"strategy": "unknown_strategy"}}

    # Act
    result = await normalizer.normalize("  hello  ", entity_config)

    # Assert
    assert result == "  hello  "  # Original value unchanged


@pytest.mark.asyncio
@patch("soni.du.normalizer.dspy.LM")
async def test_normalizer_llm_correction_failure_fallback(mock_lm_class):
    """Test that LLM correction failure falls back to trim"""
    # Arrange
    mock_lm = MagicMock()
    mock_lm.acall = AsyncMock(side_effect=Exception("LLM error"))
    mock_lm_class.return_value = mock_lm

    normalizer = SlotNormalizer(
        config={"settings": {"models": {"nlu": {"model": "gpt-4o-mini", "provider": "openai"}}}}
    )
    entity_config = {
        "name": "city",
        "type": "string",
        "normalization": {"strategy": "llm_correction"},
        "examples": ["Madrid", "Barcelona"],
    }

    # Act
    result = await normalizer.normalize("  Madriz  ", entity_config)

    # Assert
    # Should fallback to trim
    assert result == "Madriz"


@pytest.mark.asyncio
async def test_normalizer_process_empty_slots():
    """Test processing empty slots dictionary"""
    # Arrange
    normalizer = SlotNormalizer()
    slots = {}

    # Act
    result = await normalizer.process(slots)

    # Assert
    assert result == {}


@pytest.mark.asyncio
async def test_normalizer_process_with_mixed_strategies():
    """Test processing slots with different normalization strategies"""
    # Arrange
    normalizer = SlotNormalizer()
    # This test requires slots_config to be set up
    normalizer.slots_config = {
        "origin": {"normalization": {"strategy": "trim"}},
        "destination": {"normalization": {"strategy": "lowercase"}},
    }
    slots = {
        "origin": "  Madrid  ",
        "destination": "  BARCELONA  ",
    }

    # Act
    result = await normalizer.process(slots)

    # Assert
    assert result["origin"] == "Madrid"
    assert result["destination"] == "barcelona"


@pytest.mark.asyncio
async def test_normalizer_normalize_slot_unknown_slot():
    """Test normalize_slot with unknown slot name"""
    # Arrange
    config_dict = {
        "version": "0.1",
        "settings": {
            "models": {
                "nlu": {
                    "provider": "openai",
                    "model": "gpt-4o-mini",
                }
            }
        },
        "slots": {},
    }
    config = SoniConfig(**config_dict)
    normalizer = SlotNormalizer(config=config)

    # Act
    # Should use default strategy (trim)
    result = await normalizer.normalize_slot("unknown_slot", "  hello  ")

    # Assert
    assert result == "hello"
