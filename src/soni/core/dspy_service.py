"""DSPy Configuration Service.

Handles bootstrapping DSPy with the correct language model settings from SoniConfig.
"""

import dspy

from soni.config import SoniConfig


class DSPyBootstrapper:
    """Bootstrapper for DSPy configuration."""

    def __init__(self, config: SoniConfig):
        self.config = config

    @staticmethod
    def bootstrap(config: SoniConfig) -> dspy.LM:
        """Static helper to bootstrap DSPy from config."""
        bootstrapper = DSPyBootstrapper(config)
        return bootstrapper.configure()

    def configure(self) -> dspy.LM:
        """Configure DSPy with the settings from config."""
        # For now, we assume OpenAI or similar compatible interface
        # In the future, this should support other providers based on config

        # M9/M10: Using dspy.LM with openai/gpt-4o-mini as default if not specified
        # This matches the SoniConfig structure usually found in settings.llm

        provider = self.config.settings.llm.provider
        model_name = self.config.settings.llm.model

        if provider == "openai":
            # dspy.LM("openai/model") format
            lm = dspy.LM(f"openai/{model_name}")
            dspy.configure(lm=lm)
            return lm

        elif provider == "anthropic":
            lm = dspy.LM(f"anthropic/{model_name}")
            dspy.configure(lm=lm)
            return lm

        else:
            # Fallback or generic support
            # Assuming 'openai' compatible if unknown
            lm = dspy.LM(f"openai/{model_name}")
            dspy.configure(lm=lm)
            return lm
