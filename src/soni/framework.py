"""Soni v3.0 Conversational Framework - Simple API.

This module provides the high-level API described in ideas.md:

    from soni import ConversationalFramework
    
    framework = ConversationalFramework()
    framework.load_flows("flows/")
    framework.compile()
    
    response = framework.run("I want to book a flight to Paris")
"""

import asyncio
import logging
from pathlib import Path
from typing import Any

from soni.runtime import RuntimeLoop

logger = logging.getLogger(__name__)


class ConversationalFramework:
    """High-level API for Soni conversational assistants.
    
    Provides a simple interface that hides LangGraph complexity.
    
    Example:
        >>> framework = ConversationalFramework()
        >>> framework.load_flows("examples/flight_booking/soni.yaml")
        >>> framework.compile()
        >>> response = framework.run("Book a flight to Paris")
        >>> print(response)
        "Where are you flying from?"
    """
    
    def __init__(self) -> None:
        """Initialize empty framework."""
        self._config_path: Path | None = None
        self._runtime: RuntimeLoop | None = None
        self._compiled = False
        self._user_id = "default"
    
    def load_flows(self, config_path: str | Path) -> "ConversationalFramework":
        """Load flow definitions from YAML config.
        
        Args:
            config_path: Path to soni.yaml or flows directory
            
        Returns:
            self for chaining
        """
        path = Path(config_path)
        
        # If directory, look for soni.yaml
        if path.is_dir():
            yaml_file = path / "soni.yaml"
            if not yaml_file.exists():
                raise FileNotFoundError(f"No soni.yaml found in {path}")
            path = yaml_file
        
        if not path.exists():
            raise FileNotFoundError(f"Config not found: {path}")
        
        self._config_path = path
        logger.info(f"Loaded flows from {path}")
        return self
    
    def compile(self) -> "ConversationalFramework":
        """Compile flows into LangGraph.
        
        Returns:
            self for chaining
        """
        if self._config_path is None:
            raise ValueError("No flows loaded. Call load_flows() first.")
        
        self._runtime = RuntimeLoop(self._config_path)
        self._compiled = True
        logger.info("Framework compiled successfully")
        return self
    
    def run(self, message: str, user_id: str | None = None) -> str:
        """Process a user message and return the response.
        
        Args:
            message: User's input message
            user_id: Optional user ID for multi-user support
            
        Returns:
            Assistant's response string
        """
        if not self._compiled or self._runtime is None:
            raise ValueError("Framework not compiled. Call compile() first.")
        
        uid = user_id or self._user_id
        
        # Run async in sync context
        return asyncio.run(self._run_async(message, uid))
    
    async def run_async(self, message: str, user_id: str | None = None) -> str:
        """Async version of run().
        
        Args:
            message: User's input message
            user_id: Optional user ID
            
        Returns:
            Assistant's response string
        """
        if not self._compiled or self._runtime is None:
            raise ValueError("Framework not compiled. Call compile() first.")
        
        return await self._run_async(message, user_id or self._user_id)
    
    async def _run_async(self, message: str, user_id: str) -> str:
        """Internal async implementation."""
        assert self._runtime is not None
        response = await self._runtime.process_message(message, user_id)
        return response
    
    def reset(self, user_id: str | None = None) -> None:
        """Reset conversation state for a user.
        
        Args:
            user_id: User ID to reset (or default user)
        """
        # TODO: Implement conversation reset
        logger.info(f"Reset conversation for user: {user_id or self._user_id}")
    
    async def cleanup(self) -> None:
        """Cleanup resources."""
        if self._runtime:
            await self._runtime.cleanup()
            self._runtime = None
            self._compiled = False


# Convenience function for quick testing
def quick_chat(config_path: str | Path) -> None:
    """Start interactive chat session.
    
    Args:
        config_path: Path to soni.yaml config
    """
    framework = ConversationalFramework()
    framework.load_flows(config_path)
    framework.compile()
    
    print("Soni Chat (type 'quit' to exit)")
    print("-" * 40)
    
    while True:
        try:
            user_input = input("You: ").strip()
            if user_input.lower() in ("quit", "exit", "q"):
                break
            if not user_input:
                continue
            
            response = framework.run(user_input)
            print(f"Bot: {response}")
        except KeyboardInterrupt:
            break
        except Exception as e:
            print(f"Error: {e}")
    
    print("Goodbye!")
