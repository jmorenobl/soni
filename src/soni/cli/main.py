"""Main CLI entry point for Soni Framework"""

import click


@click.group()
@click.version_option(version="0.0.1", prog_name="soni")
def cli():
    """Soni Framework - Open Source Conversational AI Framework"""
    pass


@cli.command()
def optimize():
    """Optimize NLU module using DSPy MIPROv2"""
    click.echo("Optimization command - Coming soon in Hito 4")


@cli.command()
def server():
    """Start the Soni API server"""
    click.echo("Server command - Coming soon in Hito 7")


if __name__ == "__main__":
    cli()
