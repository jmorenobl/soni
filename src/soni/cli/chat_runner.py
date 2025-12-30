"""Interactive chat runner for Soni CLI."""

import importlib
import os
import sys
import uuid
from contextlib import AbstractAsyncContextManager
from dataclasses import dataclass
from pathlib import Path

from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.checkpoint.memory import MemorySaver
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
from rich.console import Console
from rich.prompt import Prompt

from soni.actions.registry import ActionRegistry
from soni.config.loader import ConfigLoader
from soni.core.dspy_service import DSPyBootstrapper
from soni.core.errors import ConfigError
from soni.core.message_sink import MessageSink
from soni.runtime.loop import RuntimeLoop

BANNER_ART = r"""
  ___  ___  _ __  _
 / __|/ _ \| '_ \| |
 \__ \ (_) | | | | |
 |___/\___/|_| |_|_|
"""


class ConsoleMessageSink(MessageSink):
    """Sink that prints to rich console."""

    def __init__(self, console: Console):
        self.console = console

    async def send(self, message: str) -> None:
        self.console.print(f"[bold blue]Soni > [/]{message}\n")


@dataclass
class ChatConfig:
    """Configuration for chat runner."""

    config_path: Path
    module: str | None = None
    thread_id: str | None = None
    model: str | None = None
    verbose: bool = False
    debug: bool = False
    streaming: bool = False


class ChatRunner:
    """Interactive chat session runner.

    Encapsulates the setup, execution, and cleanup of an
    interactive chat session with the Soni runtime.
    """

    def __init__(self, config: ChatConfig):
        """Initialize chat runner.

        Args:
            config: Chat configuration
        """
        self.config = config
        self.console = Console()
        self.runtime: RuntimeLoop | None = None
        self.thread_id = config.thread_id or f"cli_{uuid.uuid4().hex[:6]}"
        self.async_checkpointer_cm: AbstractAsyncContextManager[AsyncSqliteSaver] | None = None
        self._running = False

    async def setup(self) -> None:
        """Initialize runtime and prepare for chat.

        Raises:
            ConfigError: If config is invalid
        """
        # 0. Load Environment Variables
        from dotenv import load_dotenv

        load_dotenv()

        # 1. Load Actions Module
        if self.config.module:
            # Ensure cwd is in python path
            cwd = os.getcwd()
            if cwd not in sys.path:
                sys.path.insert(0, cwd)

            try:
                importlib.import_module(self.config.module)
                if self.config.verbose:
                    self.console.print(f"[dim]Loaded module: {self.config.module}[/]")
            except Exception as e:
                self.console.print(f"[red]Failed to load module {self.config.module}: {e}[/]")
                raise

        # 2. Load Config
        try:
            soni_config = ConfigLoader.load(self.config.config_path)
        except ConfigError as e:
            self.console.print(f"[red]Invalid config: {e}[/]")
            raise

        # 3. Setup DSPy
        try:
            bootstrapper = DSPyBootstrapper(soni_config)
            # Use specific model if provided in config overrides
            # (DSPyBootstrapper uses soni_config internal settings)
            bootstrapper.configure()
        except Exception as e:
            self.console.print(f"[red]DSPy config failed: {e}[/]")
            raise

        # 4. Setup Persistence
        persistence_cfg = soni_config.settings.persistence
        checkpointer: BaseCheckpointSaver | None = None

        if persistence_cfg.backend == "sqlite":
            self.async_checkpointer_cm = AsyncSqliteSaver.from_conn_string(persistence_cfg.path)
            if self.async_checkpointer_cm is not None:
                checkpointer = await self.async_checkpointer_cm.__aenter__()
        else:
            checkpointer = MemorySaver()

        # 5. Initialize Runtime
        # Use default registry to pick up actions registered via decorators
        registry = ActionRegistry.get_default()
        sink = ConsoleMessageSink(self.console)

        self.runtime = RuntimeLoop(
            config=soni_config,
            checkpointer=checkpointer,
            action_registry=registry,
            message_sink=sink,
        )
        await self.runtime.__aenter__()

    async def start(self) -> None:
        """Start the interactive session."""
        if not self.runtime:
            await self.setup()

        self.console.print(BANNER_ART, style="bold blue")
        self.console.print(f"Session ID: [green]{self.thread_id}[/]")
        if self.config.streaming:
            self.console.print("[yellow]Streaming not yet supported - disabling[/]")

        self.console.print("Type 'exit' or 'quit' to end session.\n")

        self._running = True
        while self._running:
            try:
                user_input = Prompt.ask("[bold green]You[/]")

                if self._is_exit_command(user_input):
                    self.console.print("\n[yellow]Goodbye![/]")
                    break

                if not user_input.strip():
                    continue

                # Process message - response is printed via ConsoleMessageSink
                if self.runtime is not None:
                    with self.console.status("[bold blue]Thinking...[/]"):
                        await self.runtime.process_message(user_input, user_id=self.thread_id)

            except KeyboardInterrupt:
                self.console.print("\n[yellow]Goodbye![/]")
                break
            except Exception as e:
                if self.config.debug:
                    self.console.print_exception()
                else:
                    self.console.print(f"[red]Error: {e}[/]")

    def _is_exit_command(self, user_input: str) -> bool:
        """Check if input is an exit command."""
        return user_input.strip().lower() in ("quit", "exit", "q", "/quit", "/exit")

    async def cleanup(self) -> None:
        """Clean up resources."""
        self._running = False
        if self.runtime is not None:
            await self.runtime.__aexit__(None, None, None)
            self.runtime = None

        if self.async_checkpointer_cm:
            await self.async_checkpointer_cm.__aexit__(None, None, None)
            self.async_checkpointer_cm = None

    async def __aenter__(self) -> "ChatRunner":
        """Async context manager entry."""
        await self.setup()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Async context manager exit."""
        await self.cleanup()


async def run_chat_session(config: ChatConfig) -> None:
    """Run an interactive chat session.

    Args:
        config: Chat configuration
    """
    async with ChatRunner(config) as runner:
        await runner.start()
