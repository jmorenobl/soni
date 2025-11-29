"""Main CLI entry point for Soni Framework"""

import typer

app = typer.Typer(
    name="soni",
    help="Soni Framework - Open Source Conversational AI Framework",
    add_completion=False,
)


def version_callback(value: bool) -> None:
    """Print version and exit"""
    if value:
        typer.echo("Soni Framework version 0.0.1")
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


@app.command()
def optimize() -> None:
    """Optimize NLU module using DSPy MIPROv2"""
    typer.echo("Optimization command - Coming soon in Hito 4")


@app.command()
def server() -> None:
    """Start the Soni API server"""
    typer.echo("Server command - Coming soon in Hito 7")


def cli() -> None:
    """Entry point for CLI"""
    app()


if __name__ == "__main__":
    cli()
