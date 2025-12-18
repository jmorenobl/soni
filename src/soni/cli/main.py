"""Main entry point for Soni CLI."""

import typer
from dotenv import load_dotenv

from soni import __version__
from soni.cli.commands import chat, optimize, server

cli = typer.Typer(
    name="soni",
    help="Soni Framework CLI - Conversational AI Engine",
    add_completion=False,
    no_args_is_help=True,
)


def version_callback(value: bool):
    if value:
        typer.echo(f"Soni Framework v{__version__}")
        raise typer.Exit()


@cli.callback()
def main(
    version: bool = typer.Option(None, "--version", "-v", callback=version_callback, is_eager=True),
):
    """
    Soni Framework CLI.
    """
    load_dotenv()


cli.add_typer(chat.app, name="chat")
cli.add_typer(optimize.app, name="optimize")
cli.add_typer(server.app, name="server")


if __name__ == "__main__":
    cli()
