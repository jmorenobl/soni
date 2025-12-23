"""Chat command for interactive sessions."""

import asyncio
import os
import uuid
from pathlib import Path

import typer
from rich.console import Console

from soni.core.errors import ConfigError
from soni.core.message_sink import MessageSink
from soni.runtime.loop import RuntimeLoop

app = typer.Typer(help="Start interactive chat with Soni")

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


class SoniChatCLI:
    """Interactive CLI for Soni conversations."""

    def __init__(
        self,
        runtime: RuntimeLoop,
        user_id: str = "cli_user",
        streaming: bool = False,
    ):
        self.console = Console()
        self.runtime = runtime
        self.user_id = user_id
        self.streaming = streaming

    async def start(self) -> None:
        """Start the interactive session."""
        self.console.print(BANNER_ART, style="bold blue")
        self.console.print(f"Session ID: [green]{self.user_id}[/]")
        if self.streaming:
            self.console.print("[yellow]Streaming not yet supported in M10 - disabling[/]")
            self.streaming = False

        self.console.print("Type 'exit' or 'quit' to end session.\n")

        while True:
            try:
                user_input = self.console.input("[bold green]You > [/]")
                if user_input.lower() in ("exit", "quit"):
                    self.console.print("\n[yellow]Goodbye![/]")
                    break

                if not user_input.strip():
                    continue

                # Process message
                with self.console.status("[bold blue]Thinking...[/]"):
                    response = await self.runtime.process_message(user_input, user_id=self.user_id)

                # Print response
                if response:
                    self.console.print(f"[bold blue]Soni > [/]{response}\n")

            except KeyboardInterrupt:
                self.console.print("\n[yellow]Goodbye![/]")
                break
            except Exception as e:
                self.console.print(f"[red]Error: {e}[/]")


@app.callback(invoke_without_command=True)
def run_chat(
    config: Path = typer.Option(
        "soni.yaml", "--config", "-c", help="Path to soni.yaml or config directory"
    ),
    module: str | None = typer.Option(
        None, "--module", "-m", help="Python module to load (e.g. 'app.actions')"
    ),
    optimized_du: bool | None = typer.Option(
        None, "--optimized-du/--no-optimized-du", help="Use optimized NLU models"
    ),
    streaming: bool = typer.Option(False, "--streaming", "-s", help="Enable streaming response"),
    user_id: str | None = typer.Option(None, "--user", "-u", help="User ID"),
    ctx: typer.Context = typer.Option(None, hidden=True),  # Inject context
) -> None:
    """Start interactive chat session."""
    if ctx.invoked_subcommand:
        return

    # 0. Load Environment Variables
    from dotenv import load_dotenv

    load_dotenv()

    # 1. Load Actions Module
    if module:
        import importlib
        import sys

        # Ensure cwd is in python path to allow importing local modules
        cwd = os.getcwd()
        if cwd not in sys.path:
            sys.path.insert(0, cwd)

        try:
            if module.endswith(".py"):
                typer.echo(
                    "Warning: Please use python module syntax (e.g. pkg.mod) for --module", err=True
                )

            importlib.import_module(module)
            typer.echo(f"Loaded module: {module}")
        except Exception as e:
            typer.echo(f"Failed to load module {module}: {e}", err=True)
            raise typer.Exit(1)

    # 2. Load Config
    from soni.config.loader import ConfigLoader

    try:
        soni_config = ConfigLoader.load(config)
    except ConfigError as e:
        typer.echo(f"Invalid config: {e}", err=True)
        raise typer.Exit(1)

    # 3. Setup DSPy using centralized bootstrapper
    from soni.core.dspy_service import DSPyBootstrapper

    try:
        bootstrapper = DSPyBootstrapper(soni_config)
        bootstrapper.configure()
    except Exception as e:
        typer.echo(f"DSPy config failed: {e}", err=True)
        raise typer.Exit(1)

    # 4. Setup Persistence (LangGraph)
    from langgraph.checkpoint.base import BaseCheckpointSaver
    from langgraph.checkpoint.memory import MemorySaver
    from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver

    persistence_cfg = soni_config.settings.persistence
    checkpointer: BaseCheckpointSaver | None = None

    try:
        if persistence_cfg.backend == "sqlite":
            # AsyncSqliteSaver requires async context or factory
            pass
        elif persistence_cfg.backend == "memory":
            checkpointer = MemorySaver()
    except Exception as e:
        typer.echo(f"Persistence init failed: {e}", err=True)
        typer.echo("Falling back to in-memory persistence.", err=True)
        checkpointer = MemorySaver()

    # 5. Initialize Runtime
    try:

        async def _bootstrap():
            # Handle AsyncSqliteSaver if needed
            nonlocal checkpointer
            async_checkpointer_cm = None

            if persistence_cfg.backend == "sqlite" and checkpointer is None:
                # We need to maintain reference to context manager to keep it open
                async_checkpointer_cm = AsyncSqliteSaver.from_conn_string(persistence_cfg.path)
                checkpointer = await async_checkpointer_cm.__aenter__()

            # Fallback
            if checkpointer is None:
                checkpointer = MemorySaver()

            # M10: Using async context manager
            from soni.actions.registry import ActionRegistry
            from soni.core.dspy_service import DSPyBootstrapper

            # Configure DSPy (LLM)
            DSPyBootstrapper.bootstrap(soni_config)

            try:
                # Use default registry to pick up actions registered via decorators
                registry = ActionRegistry.get_default()
                console = Console()
                sink = ConsoleMessageSink(console)

                async with RuntimeLoop(
                    config=soni_config,
                    checkpointer=checkpointer,
                    action_registry=registry,
                    message_sink=sink,
                ) as runtime:
                    chat = SoniChatCLI(
                        runtime,
                        user_id=user_id or f"cli_{uuid.uuid4().hex[:6]}",
                        streaming=streaming,
                    )
                    # Sync console instance
                    chat.console = console
                    await chat.start()
            finally:
                if async_checkpointer_cm:
                    await async_checkpointer_cm.__aexit__(None, None, None)

        asyncio.run(_bootstrap())

    except Exception as e:
        typer.echo(f"Runtime error: {e}", err=True)
        raise typer.Exit(1)
