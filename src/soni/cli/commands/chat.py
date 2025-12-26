"""Chat command for interactive sessions."""

import asyncio
from pathlib import Path

import typer

app = typer.Typer(help="Start interactive chat with Soni")


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
    debug: bool = typer.Option(False, "--debug", help="Debug mode"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Verbose mode"),
    ctx: typer.Context = typer.Option(None, hidden=True),  # Inject context
) -> None:
    """Start interactive chat session."""
    if ctx and ctx.invoked_subcommand:
        return

    from soni.cli.chat_runner import ChatConfig, run_chat_session

    chat_config = ChatConfig(
        config_path=config,
        module=module,
        thread_id=user_id,
        streaming=streaming,
        debug=debug,
        verbose=verbose,
    )

    try:
        asyncio.run(run_chat_session(chat_config))
    except KeyboardInterrupt:
        pass
    except Exception as e:
        typer.echo(f"Fatal error: {e}", err=True)
        raise typer.Exit(1)
