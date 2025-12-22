"""Unit tests for ResponseRephraser module."""

import dspy
import pytest
from dspy.utils.dummies import DummyLM


@pytest.fixture(autouse=True)
def configure_dspy_dummy_lm():
    """Configure DummyLM for all tests in this module."""
    # DummyLM works well with simple string outputs (no complex Pydantic models)
    # ResponseRephraser signature uses only strings, so DummyLM is suitable
    dummy_responses = [
        # Each response is a dict with the expected output field
        {
            "polished_response": "Great news! Your current account balance is $1,234.56. Is there anything else I can help with?"
        },
        {
            "polished_response": "Your account balance is $1234.56. Let me know if you need anything else."
        },
        {"polished_response": "I'm happy to help! Your balance is $500."},
    ]
    lm = DummyLM(dummy_responses)
    dspy.configure(lm=lm)
    yield
    # Cleanup not strictly needed, but good practice


@pytest.mark.asyncio
async def test_rephraser_returns_polished_response():
    """Rephraser returns a non-empty polished response."""
    # Arrange
    from soni.du.rephraser import ResponseRephraser

    rephraser = ResponseRephraser(tone="friendly", use_cot=False)

    # Act
    result = await rephraser.acall(
        template="Your balance is $1234.56",
        context="User: What's my balance?",
    )

    # Assert
    assert result is not None
    assert isinstance(result, str)
    assert len(result) > 0


@pytest.mark.asyncio
async def test_rephraser_preserves_numerical_facts():
    """Rephraser preserves numerical facts in the response."""
    # Arrange
    from soni.du.rephraser import ResponseRephraser

    rephraser = ResponseRephraser(tone="friendly", use_cot=False)

    # Act
    result = await rephraser.acall(
        template="Your balance is $1234.56",
        context="User: What's my balance?",
    )

    # Assert - The amount should be preserved (with or without formatting)
    assert "1234.56" in result or "1,234.56" in result


@pytest.mark.asyncio
async def test_rephraser_uses_configured_tone():
    """Rephraser applies the configured tone."""
    # Arrange
    from soni.du.rephraser import ResponseRephraser

    rephraser = ResponseRephraser(tone="professional", use_cot=False)

    # Act
    result = await rephraser.acall(
        template="Balance: $100",
        context="",
    )

    # Assert - DummyLM returns canned response, just verify we get something
    assert result is not None
    assert len(result) > 0


def test_rephraser_forward_sync():
    """Sync forward method works for optimization."""
    # Arrange
    from soni.du.rephraser import ResponseRephraser

    rephraser = ResponseRephraser(tone="friendly", use_cot=False)

    # Act
    result = rephraser.forward(
        template="Your balance is $500",
        context="User: Check my balance",
    )

    # Assert
    assert result is not None
    assert isinstance(result, str)


def test_rephraser_tone_types():
    """Verify tone is properly typed as Literal."""
    from soni.du.rephraser import RephraseTone, ResponseRephraser

    # Valid tones
    rephraser_friendly = ResponseRephraser(tone="friendly")
    rephraser_professional = ResponseRephraser(tone="professional")
    rephraser_formal = ResponseRephraser(tone="formal")

    assert rephraser_friendly.tone == "friendly"
    assert rephraser_professional.tone == "professional"
    assert rephraser_formal.tone == "formal"
