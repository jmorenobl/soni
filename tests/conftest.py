"""Global pytest configuration for Soni tests

This module configures the test environment, including:
- Loading environment variables from .env
- Configuring DSPy with OpenAI LM
- Shared fixtures
"""

import importlib
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
def clear_registries():
    """
    Automatically clear ActionRegistry and ValidatorRegistry before each test.

    This ensures tests don't interfere with each other through shared registry state.
    Built-in validators are re-imported after clearing to ensure they're available.
    """
    from soni.actions.registry import ActionRegistry
    from soni.validation.registry import ValidatorRegistry

    # Clear both registries before test
    ActionRegistry.clear()
    ValidatorRegistry.clear()

    # Re-import built-in validators to ensure they're registered
    # This is needed because some tests depend on built-in validators
    # Use reload() to force re-registration after clearing
    import soni.validation.validators  # noqa: F401

    importlib.reload(soni.validation.validators)

    yield

    # Clear after test (in case test registered something)
    ActionRegistry.clear()
    ValidatorRegistry.clear()


@pytest.fixture
async def runtime_loop():
    """
    Fixture that provides a RuntimeLoop instance with automatic cleanup.

    This fixture handles the creation and cleanup of RuntimeLoop instances,
    ensuring resources are properly released after each test.

    Usage:
        async def test_something(runtime_loop):
            runtime = await runtime_loop("examples/flight_booking/soni.yaml")
            # Use runtime...
            # Cleanup happens automatically
    """
    from pathlib import Path

    from soni.runtime import RuntimeLoop

    runtimes = []

    async def _create_runtime(config_path: str | Path, **kwargs) -> RuntimeLoop:
        """Create a RuntimeLoop with the given config path and options"""
        runtime = RuntimeLoop(Path(config_path), **kwargs)
        runtimes.append(runtime)
        return runtime

    yield _create_runtime

    # Cleanup all created runtimes
    for runtime in runtimes:
        await runtime.cleanup()
