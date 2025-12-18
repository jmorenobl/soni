"""DSPy bootstrapping service.

Provides unified DSPy configuration and language model setup,
eliminating duplication across CLI commands and server initialization.
"""

import logging
import os
from dataclasses import dataclass
from typing import Any

import dspy

from soni.core.config import SoniConfig
from soni.core.errors import ConfigError

logger = logging.getLogger(__name__)


@dataclass
class DSPyBootstrapResult:
    """Result of DSPy bootstrap operation."""

    lm: Any  # dspy.LM instance
    provider: str
    model: str


class DSPyBootstrapper:
    """Service for configuring DSPy language models.

    Centralizes:
    - LM initialization from config
    - API key resolution from environment
    - DSPy global configuration

    Usage:
        config = SoniConfig.from_yaml("soni.yaml")
        bootstrapper = DSPyBootstrapper(config)
        result = bootstrapper.configure()  # Returns DSPyBootstrapResult
    """

    # Environment variable names for API keys per provider
    API_KEY_ENV_VARS: dict[str, str] = {
        "openai": "OPENAI_API_KEY",
        "anthropic": "ANTHROPIC_API_KEY",
        "google": "GOOGLE_API_KEY",
        "azure": "AZURE_OPENAI_API_KEY",
    }

    def __init__(self, config: SoniConfig) -> None:
        """Initialize bootstrapper with configuration.

        Args:
            config: Soni configuration containing NLU model settings.
        """
        self.config = config
        self._lm: Any = None

    def configure(self, set_global: bool = True) -> DSPyBootstrapResult:
        """Configure DSPy with language model from settings.

        Args:
            set_global: If True, calls dspy.configure() to set global LM.
                        Set to False if you want to manage LM context manually.

        Returns:
            DSPyBootstrapResult with initialized LM.

        Raises:
            ConfigError: If API key not found or LM initialization fails.
        """
        nlu_settings = self.config.settings.models.nlu

        # Resolve API key
        api_key = self._resolve_api_key(nlu_settings.provider)

        # Create LM instance
        try:
            model_str = f"{nlu_settings.provider}/{nlu_settings.model}"
            self._lm = dspy.LM(
                model_str,
                api_key=api_key,
                temperature=nlu_settings.temperature,
            )
            logger.info(f"Initialized DSPy LM: {model_str}")

        except Exception as e:
            raise ConfigError(f"Failed to initialize DSPy LM: {e}") from e

        # Set global configuration if requested
        if set_global:
            dspy.configure(lm=self._lm)
            logger.debug("DSPy global configuration set")

        return DSPyBootstrapResult(
            lm=self._lm,
            provider=nlu_settings.provider,
            model=nlu_settings.model,
        )

    def _resolve_api_key(self, provider: str) -> str:
        """Resolve API key from environment for given provider.

        Args:
            provider: Provider name (openai, anthropic, etc.)

        Returns:
            API key string.

        Raises:
            ConfigError: If API key not found in environment.
        """
        env_var = self.API_KEY_ENV_VARS.get(provider, f"{provider.upper()}_API_KEY")
        api_key = os.getenv(env_var)

        if not api_key:
            raise ConfigError(f"API key not found. Set environment variable: {env_var}")

        return api_key

    @property
    def lm(self) -> Any:
        """Get the configured LM instance (after configure() is called)."""
        if self._lm is None:
            raise RuntimeError("DSPy not configured. Call configure() first.")
        return self._lm
