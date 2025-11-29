"""CLI command for starting Soni server"""

import logging
import os
from pathlib import Path

import typer
import uvicorn

from soni.core.config import ConfigLoader
from soni.core.errors import ConfigurationError

logger = logging.getLogger(__name__)

app = typer.Typer(
    name="server",
    help="Start the Soni API server",
    add_completion=False,
)


@app.command()
def start(
    config: str = typer.Option(
        "examples/flight_booking/soni.yaml",
        "--config",
        "-c",
        help="Path to Soni configuration YAML file",
    ),
    host: str = typer.Option(
        "0.0.0.0",
        "--host",
        "-h",
        help="Host to bind the server to",
    ),
    port: int = typer.Option(
        8000,
        "--port",
        "-p",
        help="Port to bind the server to",
    ),
    reload: bool = typer.Option(
        False,
        "--reload",
        help="Enable auto-reload (development only)",
    ),
) -> None:
    """
    Start the Soni API server.

    This command:
    1. Validates the configuration file
    2. Sets environment variables for the FastAPI app
    3. Starts uvicorn server with the FastAPI app

    Args:
        config: Path to configuration YAML file
        host: Host to bind server to
        port: Port to bind server to
        reload: Enable auto-reload for development
    """
    # Validate port range
    if port < 1 or port > 65535:
        typer.echo(f"Error: Port must be between 1 and 65535, got {port}", err=True)
        raise typer.Exit(1)

    # Validate config file exists
    config_path = Path(config)
    if not config_path.exists():
        typer.echo(f"Error: Configuration file not found: {config_path}", err=True)
        raise typer.Exit(1)

    # Validate config file is valid YAML
    try:
        ConfigLoader.load(config_path)
        typer.echo(f"✓ Configuration loaded: {config_path}")
    except ConfigurationError as e:
        typer.echo(f"Error: Invalid configuration: {e}", err=True)
        raise typer.Exit(1) from e

    # Set environment variable for FastAPI app
    os.environ["SONI_CONFIG_PATH"] = str(config_path.absolute())

    # Optional: Set optimized DU path if provided
    optimized_du_path = os.getenv("SONI_OPTIMIZED_DU_PATH")
    if optimized_du_path:
        du_path = Path(optimized_du_path)
        if du_path.exists():
            typer.echo(f"✓ Optimized DU module: {du_path}")
        else:
            typer.echo(f"Warning: Optimized DU path not found: {du_path}", err=True)

    # Display startup information
    typer.echo("\n🚀 Starting Soni server...")
    typer.echo(f"   Config: {config_path.absolute()}")
    typer.echo(f"   Host: {host}")
    typer.echo(f"   Port: {port}")
    typer.echo(f"   Reload: {reload}")
    typer.echo("\n📚 API Documentation:")
    typer.echo(f"   Swagger UI: http://{host}:{port}/docs")
    typer.echo(f"   ReDoc: http://{host}:{port}/redoc")
    typer.echo("\n💬 Endpoints:")
    typer.echo(f"   Health: http://{host}:{port}/health")
    typer.echo(f"   Chat: http://{host}:{port}/chat/{{user_id}}")
    typer.echo("\n")

    # Start uvicorn server
    try:
        uvicorn.run(
            "soni.server.api:app",
            host=host,
            port=port,
            reload=reload,
            log_level="info",
        )
    except KeyboardInterrupt:
        typer.echo("\n\n👋 Shutting down Soni server...")
    except Exception as e:
        typer.echo(f"\n❌ Error starting server: {e}", err=True)
        raise typer.Exit(1) from e
