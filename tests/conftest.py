"""Global pytest configuration for Soni tests

This module configures the test environment, including:
- Loading environment variables from .env
- Configuring DSPy with OpenAI LM
- Shared fixtures
- Suppressing warnings from external dependencies
"""

import importlib
import os
import warnings
from pathlib import Path

# Import dependencies first
import dspy  # noqa: E402
import pytest  # noqa: E402
from dotenv import load_dotenv  # noqa: E402


# Load .env file from project root
def pytest_configure(config):
    """Configure pytest environment before tests run"""
    # Note: Warning filters are configured in pyproject.toml [tool.pytest.ini_options]
    # This ensures warnings from external dependencies are suppressed from the start

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


def configure_test_config_for_memory(config):
    """
    Helper function to configure a SoniConfig instance to use memory backend for tests.

    This ensures tests use MemorySaver instead of SQLite, providing:
    - Faster test execution (no I/O)
    - Better test isolation (no shared database state)
    - No need for database cleanup

    SQLite should only be used for development, not for tests.

    Args:
        config: SoniConfig instance to modify

    Returns:
        Modified SoniConfig instance (same object, modified in place)
    """
    if hasattr(config, "settings") and hasattr(config.settings, "persistence"):
        config.settings.persistence.backend = "memory"
    return config


def load_test_config(config_path: str | Path):
    """
    Load a SoniConfig from YAML file and configure it for testing (memory backend).

    This is a convenience function for tests that need to load configuration files.
    It automatically configures the persistence backend to 'memory' for faster,
    isolated tests.

    Args:
        config_path: Path to YAML configuration file

    Returns:
        SoniConfig instance configured with memory backend
    """
    from soni.core.config import SoniConfig

    config = SoniConfig.from_yaml(config_path)
    return configure_test_config_for_memory(config)


@pytest.fixture
async def runtime_loop():
    """
    Fixture that provides a RuntimeLoop instance with automatic cleanup.

    This fixture handles the creation and cleanup of RuntimeLoop instances,
    ensuring resources are properly released after each test.
    Automatically configures memory backend for tests to avoid SQLite warnings.

    Usage:
        async def test_something(runtime_loop):
            runtime = await runtime_loop("examples/flight_booking/soni.yaml")
            # Use runtime...
            # Cleanup happens automatically
    """
    import tempfile
    from pathlib import Path

    import yaml

    from soni.runtime import RuntimeLoop

    runtimes = []
    temp_files = []

    async def _create_runtime(config_path: str | Path, **kwargs) -> RuntimeLoop:
        """Create a RuntimeLoop with the given config path and options"""
        # Load config and configure memory backend for tests
        config = load_test_config(config_path)

        # Create temporary config file with memory backend
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(config.model_dump(), f)
            temp_config_path = f.name
            temp_files.append(temp_config_path)

        runtime = RuntimeLoop(Path(temp_config_path), **kwargs)
        runtimes.append(runtime)
        return runtime

    yield _create_runtime

    # Cleanup all created runtimes
    for runtime in runtimes:
        await runtime.cleanup()

    # Cleanup temporary config files
    for temp_file in temp_files:
        Path(temp_file).unlink(missing_ok=True)


@pytest.fixture
async def runtime():
    """Create RuntimeLoop with in-memory checkpointer for test isolation.

    This fixture is similar to the one in test_e2e.py but available globally.
    It creates a RuntimeLoop instance with memory backend for fast, isolated tests.
    """
    import tempfile

    import yaml

    from soni.core.config import ConfigLoader, SoniConfig
    from soni.runtime import RuntimeLoop

    # Use flight booking example as default config
    config_path = Path("examples/flight_booking/soni.yaml")

    # Import actions from original config directory before creating RuntimeLoop
    config_dir = config_path.parent

    # Try importing actions.py (primary convention)
    actions_file = config_dir / "actions.py"
    if actions_file.exists():
        import importlib.util

        spec = importlib.util.spec_from_file_location("user_actions", actions_file)
        if spec and spec.loader:
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)

    # Try importing __init__.py (package convention - imports handlers.py)
    init_file = config_dir / "__init__.py"
    if init_file.exists():
        import importlib
        import sys

        package_name = config_dir.name
        parent_dir = config_dir.parent
        original_path = sys.path[:]
        try:
            if str(parent_dir) not in sys.path:
                sys.path.insert(0, str(parent_dir))
            importlib.import_module(package_name)
        finally:
            sys.path[:] = original_path

    # Load config and modify persistence backend to memory
    config_dict = ConfigLoader.load(config_path)
    config = SoniConfig(**config_dict)
    config.settings.persistence.backend = "memory"

    # Create temporary config file with memory backend
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        yaml.dump(config.model_dump(), f)
        temp_config_path = f.name

    try:
        runtime_instance = RuntimeLoop(temp_config_path)
        # Initialize graph eagerly for tests (lazy initialization causes issues)
        await runtime_instance._ensure_graph_initialized()
        yield runtime_instance
        await runtime_instance.cleanup()
    finally:
        # Cleanup temporary config file
        Path(temp_config_path).unlink(missing_ok=True)
