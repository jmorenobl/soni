"""Global pytest configuration for Soni tests

This module configures the test environment, including:
- Loading environment variables from .env
- Configuring DSPy with OpenAI LM
- Shared fixtures
"""

import os
from pathlib import Path

import dspy
import pytest
from dotenv import load_dotenv


# Load .env file from project root
def pytest_configure(config):
    """Configure pytest environment before tests run"""
    # Load .env from project root (parent of tests/)
    project_root = Path(__file__).parent.parent
    env_path = project_root / ".env"

    # Check if API key is already in environment (from shell or CI)
    api_key_from_env = os.getenv("OPENAI_API_KEY")

    if env_path.exists():
        # Load .env file (override=False means env vars take precedence)
        # This allows CI/CD to override .env values
        load_dotenv(env_path, override=False)
        print(f"\n✅ Loaded environment from {env_path}")
    else:
        print(f"\n⚠️  No .env file found at {env_path}")

    # Check API key after loading .env
    api_key = os.getenv("OPENAI_API_KEY")
    if api_key:
        # Verify it's not empty
        if api_key.strip():
            try:
                lm = dspy.LM("openai/gpt-4o-mini", api_key=api_key)
                dspy.configure(lm=lm)
                source = "environment variable" if api_key_from_env else ".env file"
                print(f"✅ DSPy configured with OpenAI LM (gpt-4o-mini) - API key from {source}")
            except Exception as e:
                print(f"⚠️  Failed to configure DSPy: {e}")
        else:
            print("⚠️  OPENAI_API_KEY is empty - LLM tests will be skipped")
    else:
        print("⚠️  OPENAI_API_KEY not found - LLM tests will be skipped")
        print(f"   Checked: {env_path} and environment variables")


@pytest.fixture(scope="session")
def has_api_key():
    """Check if OpenAI API key is available"""
    return os.getenv("OPENAI_API_KEY") is not None


@pytest.fixture(scope="session")
def skip_without_api_key(has_api_key):
    """Skip test if API key is not available"""
    if not has_api_key:
        pytest.skip("OPENAI_API_KEY not configured")


@pytest.fixture(autouse=True)
def clear_action_registry():
    """
    Automatically clear ActionRegistry before each test to avoid state leakage.

    This ensures tests don't interfere with each other through shared registry state.
    """
    from soni.actions.registry import ActionRegistry

    # Clear before test
    ActionRegistry.clear()
    yield
    # Clear after test (in case test registered something)
    ActionRegistry.clear()
