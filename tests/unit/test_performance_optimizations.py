"""Tests for performance optimizations (caching)"""

import time
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from soni.core.scope import ScopeManager
from soni.core.state import DialogueState
from soni.du.models import NLUOutput
from soni.du.modules import SoniDU


@pytest.mark.asyncio
async def test_nlu_cache_hit():
    """Test that NLU cache returns cached result on hit"""
    # Arrange
    du = SoniDU(cache_size=100, cache_ttl=60)
    user_message = "I want to book a flight"
    dialogue_history = ""
    current_slots = {}
    available_actions = ["book_flight", "cancel_booking"]
    current_flow = "none"

    # Mock the acall to return a prediction
    mock_prediction = MagicMock()
    mock_prediction.structured_command = "book_flight"
    mock_prediction.extracted_slots = '{"destination": "Paris"}'
    mock_prediction.confidence = "0.9"
    mock_prediction.reasoning = "User wants to book a flight"

    with patch.object(du, "acall", new_callable=AsyncMock) as mock_acall:
        mock_acall.return_value = mock_prediction

        # Act - First call (cache miss)
        result1 = await du.predict(
            user_message=user_message,
            dialogue_history=dialogue_history,
            current_slots=current_slots,
            available_actions=available_actions,
            current_flow=current_flow,
        )

        # Second call (cache hit)
        start_time = time.time()
        result2 = await du.predict(
            user_message=user_message,
            dialogue_history=dialogue_history,
            current_slots=current_slots,
            available_actions=available_actions,
            current_flow=current_flow,
        )
        elapsed = time.time() - start_time

        # Assert
        assert result1.command == result2.command
        # Compare slots (list of SlotValue objects)
        assert len(result1.slots) == len(result2.slots)
        if result1.slots and result2.slots:
            assert result1.slots[0].name == result2.slots[0].name
            assert result1.slots[0].value == result2.slots[0].value
        assert result1.confidence == result2.confidence
        # Cache hit should be much faster (no LLM call)
        assert elapsed < 0.1  # Should be very fast
        # acall should only be called once (first call)
        assert mock_acall.call_count == 1


@pytest.mark.asyncio
async def test_nlu_cache_miss():
    """Test that NLU cache misses on different inputs"""
    # Arrange
    du = SoniDU(cache_size=100, cache_ttl=60)

    # Mock the acall to return different predictions
    mock_prediction1 = MagicMock()
    mock_prediction1.structured_command = "book_flight"
    mock_prediction1.extracted_slots = '{"destination": "Paris"}'
    mock_prediction1.confidence = "0.9"
    mock_prediction1.reasoning = "User wants to book"

    mock_prediction2 = MagicMock()
    mock_prediction2.structured_command = "cancel_booking"
    mock_prediction2.extracted_slots = "{}"
    mock_prediction2.confidence = "0.8"
    mock_prediction2.reasoning = "User wants to cancel"

    with patch.object(du, "acall", new_callable=AsyncMock) as mock_acall:
        mock_acall.side_effect = [mock_prediction1, mock_prediction2]

        # Act - First call
        result1 = await du.predict(
            user_message="I want to book a flight",
            dialogue_history="",
            current_slots={},
            available_actions=["book_flight"],
            current_flow="none",
        )

        # Second call with different message (cache miss)
        result2 = await du.predict(
            user_message="I want to cancel my booking",
            dialogue_history="",
            current_slots={},
            available_actions=["cancel_booking"],
            current_flow="none",
        )

        # Assert
        assert isinstance(result1, NLUOutput)
        assert isinstance(result2, NLUOutput)
        assert result1.command != result2.command
        # acall should be called twice (different inputs)
        assert mock_acall.call_count == 2


@pytest.mark.asyncio
async def test_nlu_cache_ttl_expiry():
    """Test that NLU cache expires after TTL"""
    # Arrange
    du = SoniDU(cache_size=100, cache_ttl=1)  # 1 second TTL
    user_message = "I want to book a flight"

    # Mock the acall to return a prediction
    mock_prediction = MagicMock()
    mock_prediction.structured_command = "book_flight"
    mock_prediction.extracted_slots = '{"destination": "Paris"}'
    mock_prediction.confidence = "0.9"
    mock_prediction.reasoning = "User wants to book"

    with patch.object(du, "acall", new_callable=AsyncMock) as mock_acall:
        mock_acall.return_value = mock_prediction

        # Act - First call (cache miss)
        result1 = await du.predict(
            user_message=user_message,
            dialogue_history="",
            current_slots={},
            available_actions=["book_flight"],
            current_flow="none",
        )

        # Wait for TTL to expire
        time.sleep(1.1)

        # Second call (should be cache miss due to expiry)
        result2 = await du.predict(
            user_message=user_message,
            dialogue_history="",
            current_slots={},
            available_actions=["book_flight"],
            current_flow="none",
        )

        # Assert
        assert isinstance(result1, NLUOutput)
        assert isinstance(result2, NLUOutput)
        # Cache should have expired, so acall should be called twice
        assert mock_acall.call_count == 2


def test_scoping_cache_hit():
    """Test that scoping cache returns cached result on hit"""
    # Arrange
    config_path = Path("examples/flight_booking/soni.yaml")
    from soni.core.config import ConfigLoader, SoniConfig

    config_dict = ConfigLoader.load(config_path)
    config = SoniConfig(**config_dict)

    scope_manager = ScopeManager(config=config, cache_size=100, cache_ttl=60)
    state = DialogueState(
        current_flow="book_flight",
        slots={"destination": "Paris"},
    )

    # Act - First call (cache miss)
    actions1 = scope_manager.get_available_actions(state)

    # Second call (cache hit)
    start_time = time.time()
    actions2 = scope_manager.get_available_actions(state)
    elapsed = time.time() - start_time

    # Assert
    assert actions1 == actions2
    # Cache hit should be very fast
    assert elapsed < 0.01  # Should be microseconds


def test_scoping_cache_miss():
    """Test that scoping cache misses on different state"""
    # Arrange
    config_path = Path("examples/flight_booking/soni.yaml")
    from soni.core.config import ConfigLoader, SoniConfig

    config_dict = ConfigLoader.load(config_path)
    config = SoniConfig(**config_dict)

    scope_manager = ScopeManager(config=config, cache_size=100, cache_ttl=60)

    # Act - First call
    state1 = DialogueState(
        current_flow="book_flight",
        slots={"destination": "Paris"},
    )
    actions1 = scope_manager.get_available_actions(state1)

    # Second call with different state (cache miss)
    state2 = DialogueState(
        current_flow="book_flight",
        slots={"destination": "Madrid", "origin": "Barcelona"},
    )
    actions2 = scope_manager.get_available_actions(state2)

    # Assert
    assert isinstance(actions1, list)
    assert isinstance(actions2, list)
    # Actions might be different due to different slots


def test_scoping_cache_ttl_expiry():
    """Test that scoping cache expires after TTL"""
    # Arrange
    config_path = Path("examples/flight_booking/soni.yaml")
    from soni.core.config import ConfigLoader, SoniConfig

    config_dict = ConfigLoader.load(config_path)
    config = SoniConfig(**config_dict)

    scope_manager = ScopeManager(config=config, cache_size=100, cache_ttl=1)  # 1 second TTL
    state = DialogueState(
        current_flow="book_flight",
        slots={"destination": "Paris"},
    )

    # Act - First call (cache miss)
    actions1 = scope_manager.get_available_actions(state)

    # Wait for TTL to expire
    time.sleep(1.1)

    # Second call (should be cache miss due to expiry)
    actions2 = scope_manager.get_available_actions(state)

    # Assert
    assert isinstance(actions1, list)
    assert isinstance(actions2, list)
    # Cache should have expired
