"""Chat command for interactive sessions."""

import asyncio
import os
import uuid
from pathlib import Path

import dspy
import typer
from rich.console import Console

from soni.core.config import SoniConfig
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

    def __init__(self, runtime: RuntimeLoop, user_id: str = "cli_user"):
        self.console = Console()
        self.runtime = runtime
        self.user_id = user_id

    async def start(self) -> None:
        """Start the interactive session."""
        self.console.print(BANNER_ART, style="bold blue")
        self.console.print(f"Session ID: [green]{self.user_id}[/]")
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
):
    """Start interactive chat session."""

    # 1. Load Config
    try:
        soni_config = SoniConfig.from_yaml(config)
    except ConfigError as e:
        typer.echo(f"Invalid config: {e}", err=True)
        raise typer.Exit(1)

    # 2. Setup DSPy
    nlu_cfg = soni_config.settings.models.nlu
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        typer.echo("Error: OPENAI_API_KEY not found.", err=True)
        raise typer.Exit(1)

    try:
        lm = dspy.LM(
            f"{nlu_cfg.provider}/{nlu_cfg.model}",
            api_key=api_key,
            temperature=nlu_cfg.temperature,
        )
        dspy.configure(lm=lm)
    except Exception as e:
        typer.echo(f"DSPy config failed: {e}", err=True)
        raise typer.Exit(1)

    # 3. Initialize Runtime
    # RuntimeLoop expects config object, not path
    # But wait, RuntimeLoop constructor signature in loop.py is:
    # def __init__(self, config: SoniConfig, checkpointer: BaseCheckpointSaver | None = None, registry: ActionRegistry | None = None):
    # So we pass the object.

    # Wait, the legacy CLI passed config_path.
    # Let's check loop.py again in previous turn.
    # Ah, I viewed loop.py. Constructor takes config: SoniConfig.
    # I will pass the object.

    try:
        # We need to manually initialize SoniDU with the optimized path if provided.
        # Ideally RuntimeLoop would handle this, or we patch it.
        # RuntimeLoop.initialize() creates a fresh SoniDU().
        # We might need to manually set it after init.

        runtime = RuntimeLoop(config=soni_config)
        # Note: We need to run async init.

        async def _bootstrap():
            await runtime.initialize()
            if optimized_du:
                # Load optimization
                # runtime.du is accessible as property
                runtime.du.load(str(optimized_du))
                typer.echo(f"Loaded optimized NLU from {optimized_du}")

            chat = SoniChatCLI(runtime, user_id=user_id or f"cli_{uuid.uuid4().hex[:6]}")
            await chat.start()

        asyncio.run(_bootstrap())

    except Exception as e:
        typer.echo(f"Runtime error: {e}", err=True)
        raise typer.Exit(1)
