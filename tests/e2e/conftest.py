"""End-to-end test configuration.

Uses REAL NLU (DSPy) with configured LM.
"""

import os

import pytest


@pytest.fixture(scope="session", autouse=True)
def setup_dspy():
    """Configure DSPy with real LM for E2E tests."""
    import dspy

    # Use OpenAI by default if key exists, otherwise warn/skip
    if os.getenv("OPENAI_API_KEY"):
        lm = dspy.LM("openai/gpt-4o-mini", temperature=0.0)
        dspy.configure(lm=lm)
    else:
        pytest.skip("OPENAI_API_KEY not set, skipping E2E tests")
