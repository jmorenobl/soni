"""Server command to start API."""

import os
from pathlib import Path

import typer
import uvicorn

from soni.config.loader import ConfigLoader

app = typer.Typer(help="Start API server")


@app.callback(invoke_without_command=True)
def start_server(
    config: Path = typer.Option(..., "--config", "-c", help="Path to soni.yaml", exists=True),
    host: str = typer.Option("0.0.0.0", "--host", "-h"),
    port: int = typer.Option(8000, "--port", "-p"),
    reload: bool = typer.Option(False, "--reload"),
):
    """Start the Soni API server."""

    # 1. Validate Config
    try:
        ConfigLoader.load(config)
    except Exception as e:
        typer.echo(f"Invalid config: {e}", err=True)
        raise typer.Exit(1)

    # 2. Set Env Vars for the server process (it loads config from env)
    os.environ["SONI_CONFIG_PATH"] = str(config.absolute())

    typer.echo(f"🚀 Starting Soni Server on http://{host}:{port}")
    typer.echo(f"   Config: {config}")

    try:
        uvicorn.run(
            "soni.server.api:app",
            host=host,
            port=port,
            reload=reload,
            log_level="info",
        )
    except Exception as e:
        typer.echo(f"Server failed: {e}", err=True)
        raise typer.Exit(1)
