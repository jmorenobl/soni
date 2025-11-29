"""Main CLI entry point for Soni Framework"""

import typer

from soni.cli import optimize as optimize_module
from soni.cli import server as server_module

app = typer.Typer(
    name="soni",
    help="Soni Framework - Open Source Conversational AI Framework",
    add_completion=False,
)

# Register subcommands
app.add_typer(optimize_module.app, name="optimize", help="Optimize NLU modules with DSPy")
app.add_typer(server_module.app, name="server", help="Start the Soni API server")


def version_callback(value: bool) -> None:
    """Print version and exit"""
    if value:
        typer.echo("Soni Framework version 0.1.0")
        raise typer.Exit()


@app.callback()
def main(
    version: bool = typer.Option(
        False,
        "--version",
        "-v",
        help="Show version and exit",
        callback=version_callback,
        is_eager=True,
    ),
) -> None:
    """Soni Framework - Open Source Conversational AI Framework"""
    pass


def cli() -> None:
    """Entry point for CLI"""
    app()


if __name__ == "__main__":
    cli()
