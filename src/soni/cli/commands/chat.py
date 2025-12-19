"""Chat command for interactive sessions."""

import asyncio
import os
import uuid
from pathlib import Path

import typer
from rich.console import Console

from soni.config import SoniConfig
from soni.core.errors import ConfigError
from soni.runtime.loop import RuntimeLoop

app = typer.Typer(help="Start interactive chat with Soni")

BANNER_ART = r"""
  ___  ___  _ __  _
 / __|/ _ \| '_ \| |
 \__ \ (_) | | | | |
 |___/\___/|_| |_|_|
"""


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

        # Re-writing start() method content logic completely in one chunk to avoid context issues

    async def start(self) -> None:
        """Start the interactive session."""
        from soni.runtime.stream_extractor import ResponseStreamExtractor

        self.console.print(BANNER_ART, style="bold blue")
        self.console.print(f"Session ID: [green]{self.user_id}[/]")
        if self.streaming:
            self.console.print("[dim]Streaming mode enabled[/]")
        self.console.print("Type 'exit' or 'quit' to end session.\n")

        extractor = ResponseStreamExtractor()

        while True:
            try:
                user_input = self.console.input("[bold green]You > [/]")
                if user_input.lower() in ("exit", "quit"):
                    self.console.print("\n[yellow]Goodbye![/]")
                    break

                if not user_input.strip():
                    continue

                if self.streaming:
                    # Streaming mode
                    self.console.print("[bold blue]Soni > [/]", end="")
                    last_response = ""

                    async for chunk in self.runtime.process_message_streaming(
                        user_input,
                        user_id=self.user_id,
                        stream_mode="updates",
                    ):
                        stream_chunk = extractor.extract(chunk, "updates")
                        if stream_chunk and stream_chunk.content:
                            # Print new content (avoid duplicates)
                            if stream_chunk.content != last_response:
                                print(stream_chunk.content, end="", flush=True)
                                last_response = stream_chunk.content

                    print()  # Newline after response
                else:
                    # Process message
                    with self.console.status("[bold blue]Thinking...[/]"):
                        response = await self.runtime.process_message(
                            user_input, user_id=self.user_id
                        )

                    # Print response
                    if response:
                        # Depending on response format (dict or object)
                        # response is usually dict from RuntimeLoop
                        text = (
                            response.get("response", "...")
                            if isinstance(response, dict)
                            else str(response)
                        )
                        self.console.print(f"[bold blue]Soni > [/]{text}\n")

            except KeyboardInterrupt:
                self.console.print("\n[yellow]Goodbye![/]")
                break
            except Exception as e:
                self.console.print(f"[red]Error: {e}[/]")


@app.callback(invoke_without_command=True)
def run_chat(
    config: Path = typer.Option(..., "--config", "-c", help="Path to soni.yaml", exists=True),
    user_id: str | None = typer.Option(None, "--user-id", "-u", help="User ID for session"),
    optimized_du: Path | None = typer.Option(
        None, "--optimized-du", "-d", help="Path to optimized NLU module", exists=True
    ),
    module: str | None = typer.Option(
        None, "--module", "-m", help="Python module to import (e.g. 'examples.banking.handlers')"
    ),
    streaming: bool = typer.Option(False, "--streaming", "-s", help="Enable streaming mode"),
):
    """Start interactive chat session."""

    # 1. Load User Code (Actions)
    if module:
        import importlib
        import sys

        # Ensure cwd is in python path to allow importing local modules
        cwd = os.getcwd()
        if cwd not in sys.path:
            sys.path.insert(0, cwd)

        try:
            # If it's a file path, convert to module notation or load by path?
            # Simpler to assume module notation for now if using -m
            # But user might pass 'examples/banking/handlers.py'
            if module.endswith(".py"):
                # Load via path not implemented yet for simplicity, suggest module syntax
                typer.echo(
                    "Warning: Please use python module syntax (e.g. pkg.mod) for --module", err=True
                )

            importlib.import_module(module)
            typer.echo(f"Loaded module: {module}")
        except Exception as e:
            typer.echo(f"Failed to load module {module}: {e}", err=True)
            # Don't exit? Or exit? Actions might be critical.
            # Let's exit to be safe.
            raise typer.Exit(1)

    # 2. Load Config
    try:
        soni_config = SoniConfig.from_yaml(config)
    except ConfigError as e:
        typer.echo(f"Invalid config: {e}", err=True)
        raise typer.Exit(1)

    # 3. Setup DSPy using centralized bootstrapper
    from soni.core.dspy_service import DSPyBootstrapper

    try:
        bootstrapper = DSPyBootstrapper(soni_config)
        dspy_result = bootstrapper.configure()
        typer.echo(f"DSPy configured: {dspy_result.provider}/{dspy_result.model}")
    except Exception as e:
        typer.echo(f"DSPy config failed: {e}", err=True)
        raise typer.Exit(1)

    # 3. Setup Persistence
    from soni.runtime.checkpointer import create_checkpointer

    persistence_cfg = soni_config.settings.persistence
    try:
        if persistence_cfg.backend == "sqlite":
            checkpointer = create_checkpointer(type="sqlite", db_path=persistence_cfg.path)
        elif persistence_cfg.backend == "memory":
            checkpointer = create_checkpointer(type="memory")
        else:
            # Fallback or error?
            # For now fallback to memory if not configured, or error if unknown backend.
            # checkpointer.py handles unknown types
            checkpointer = create_checkpointer(
                type=persistence_cfg.backend,
                # Pass other kwargs generically if needed, but for now specific mapping is safer
                # or pass path as db_path/connection_string generically?
                # create_checkpointer takes kwargs.
                # sqlite takes db_path. postgres takes connection_string.
                db_path=persistence_cfg.path,
                connection_string=persistence_cfg.path,
            )
    except Exception as e:
        typer.echo(f"Persistence init failed: {e}", err=True)
        # Fallback to memory for CLI chat might be acceptable but let's warn
        typer.echo("Falling back to in-memory persistence.", err=True)
        checkpointer = create_checkpointer(type="memory")

    # 4. Initialize Runtime
    try:
        # We need to manually initialize SoniDU with the optimized path if provided.
        # Ideally RuntimeLoop would handle this, or we patch it.
        # RuntimeLoop.initialize() creates a fresh SoniDU().
        # We might need to manually set it after init.

        runtime = RuntimeLoop(config=soni_config, checkpointer=checkpointer)
        # Note: We need to run async init.

        async def _bootstrap():
            await runtime.initialize()
            if optimized_du:
                # Load optimization
                # runtime.du is accessible as property
                if hasattr(runtime.du, "load"):
                    runtime.du.load(str(optimized_du))
                    typer.echo(f"Loaded optimized NLU from {optimized_du}")
                else:
                    typer.echo(
                        "Warning: Current NLU provider does not support loading optimization.",
                        err=True,
                    )

            chat = SoniChatCLI(
                runtime,
                user_id=user_id or f"cli_{uuid.uuid4().hex[:6]}",
                streaming=streaming,
            )
            await chat.start()

        asyncio.run(_bootstrap())

    except Exception as e:
        typer.echo(f"Runtime error: {e}", err=True)
        raise typer.Exit(1)
