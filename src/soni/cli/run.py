"""CLI command for interactive Soni conversation"""

import asyncio
import os
import sys
from pathlib import Path

import dspy
import typer
from dotenv import load_dotenv
from rich.align import Align
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.prompt import Prompt

from soni.core.config import SoniConfig
from soni.core.errors import ConfigurationError, NLUError, ValidationError
from soni.runtime import RuntimeLoop

# Banner ASCII art for Soni
BANNER_ART = r"""
 ███████╗██████╗ ███╗   ██╗██╗
██╔════╝██╔═══██╗████╗  ██║██║
███████╗██║   ██║██╔██╗ ██║██║
╚════██║██║   ██║██║╚██╗██║██║
███████║╚██████╔╝██║ ╚████║██║
╚══════╝ ╚═════╝ ╚═╝  ╚═══╝╚═╝
"""

app = typer.Typer(
    name="run",
    help="Start interactive conversation with Soni",
    add_completion=False,
)


class SoniChatCLI:
    """Interactive CLI for Soni conversations."""

    def __init__(self, runtime: RuntimeLoop, user_id: str = "cli_user"):
        """
        Initialize CLI with runtime.

        Args:
            runtime: Initialized RuntimeLoop instance
            user_id: User ID for conversation (default: "cli_user")
        """
        self.console = Console()
        self.runtime = runtime
        self.user_id = user_id

    def print_banner(self) -> None:
        """Render banner with style."""
        self.console.clear()
        banner_panel = Panel(
            Align.center(BANNER_ART),
            style="bold cyan",
            border_style="blue",
            subtitle="[dim]Soni Framework - Interactive Conversation[/dim]",
        )
        self.console.print(banner_panel)
        self.console.print(
            "[italic green]Conversation started. Type 'exit', 'quit', or 'salir' to end.[/]\n"
        )

    async def start(self) -> None:
        """Start interactive conversation loop."""
        self.print_banner()

        while True:
            try:
                # Get user input
                user_input = Prompt.ask("[bold green]You[/]")

                # Check for exit commands
                if user_input.lower() in ["exit", "quit", "salir", "q"]:
                    self.console.print("[yellow]Ending conversation...[/]")
                    break

                if not user_input.strip():
                    continue

                # Process message with spinner
                with self.console.status("[bold blue]Processing message...[/]", spinner="dots"):
                    try:
                        response_text = await self.runtime.process_message(
                            user_msg=user_input, user_id=self.user_id
                        )
                    except ValidationError as e:
                        self.console.print(
                            Panel(
                                f"[red]Validation Error:[/] {str(e)}",
                                title="[bold red]Error[/]",
                                border_style="red",
                            )
                        )
                        continue
                    except NLUError as e:
                        self.console.print(
                            Panel(
                                f"[red]NLU Error:[/] {str(e)}",
                                title="[bold red]Error[/]",
                                border_style="red",
                            )
                        )
                        continue

                # Render response (supports Markdown)
                self.console.print(
                    Panel(
                        Markdown(response_text),
                        title="[bold blue]Soni[/]",
                        border_style="blue",
                        expand=False,
                    )
                )
                self.console.print("")  # Spacing

            except KeyboardInterrupt:
                self.console.print("\n[red]Interrupted. Exiting...[/]")
                sys.exit(0)
            except Exception as e:
                self.console.print(
                    Panel(
                        f"[red]Unexpected error:[/] {str(e)}",
                        title="[bold red]Error[/]",
                        border_style="red",
                    )
                )
                self.console.print("")  # Spacing


@app.callback(invoke_without_command=True)
def run(
    config: str = typer.Option(
        "examples/flight_booking/soni.yaml",
        "--config",
        "-c",
        help="Path to Soni configuration YAML file",
    ),
    user_id: str = typer.Option(
        None,
        "--user-id",
        "-u",
        help="User ID for conversation session (random if not specified)",
    ),
    optimized_du: str | None = typer.Option(
        None,
        "--optimized-du",
        "-d",
        help="Path to optimized DU module (JSON)",
    ),
    handlers: str | None = typer.Option(
        None,
        "--handlers",
        "-h",
        help="Python module path containing action handlers (e.g., 'examples.banking.handlers')",
    ),
) -> None:
    """
    Start interactive conversation with Soni.

    This command:
    1. Validates the configuration file
    2. Initializes RuntimeLoop
    3. Starts interactive conversation loop

    Args:
        config: Path to configuration YAML file
        user_id: User ID for conversation session
        optimized_du: Optional path to optimized DU module
    """
    # Load environment variables from .env file if it exists
    load_dotenv()

    # Generate random user_id if not specified
    import uuid

    if user_id is None:
        user_id = f"cli_{uuid.uuid4().hex[:8]}"

    # Validate config file exists
    config_path = Path(config)
    if not config_path.exists():
        typer.echo(f"Error: Configuration file not found: {config_path}", err=True)
        raise typer.Exit(1)

    # Load and validate configuration
    try:
        soni_config = SoniConfig.from_yaml(config_path)
    except ConfigurationError as e:
        typer.echo(f"Error: Invalid configuration: {e}", err=True)
        raise typer.Exit(1) from e

    # Configure DSPy from settings
    nlu_config = soni_config.settings.models.nlu
    provider = nlu_config.provider
    model_name = nlu_config.model
    temperature = nlu_config.temperature

    # Get API key from environment
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        typer.echo(
            "⚠️  OPENAI_API_KEY not found. Please set it in your environment or .env file",
            err=True,
        )
        typer.echo("   Example: export OPENAI_API_KEY='your-api-key'", err=True)
        raise typer.Exit(1)

    # Configure DSPy with LM from settings
    try:
        lm = dspy.LM(f"{provider}/{model_name}", api_key=api_key, temperature=temperature)
        dspy.configure(lm=lm)
        typer.echo(f"✓ DSPy configured with {provider}/{model_name} (temperature={temperature})")
    except Exception as e:
        typer.echo(f"Error: Failed to configure DSPy: {e}", err=True)
        raise typer.Exit(1) from e

    # Validate optimized DU path if provided
    optimized_du_path = None
    if optimized_du:
        optimized_du_path_obj = Path(optimized_du)
        if not optimized_du_path_obj.exists():
            typer.echo(f"Error: Optimized DU file not found: {optimized_du_path_obj}", err=True)
            raise typer.Exit(1)
        optimized_du_path = optimized_du_path_obj

    # Load custom handlers module if specified
    if handlers:
        try:
            import importlib

            _handlers_module = importlib.import_module(handlers)  # noqa: F841
            typer.echo(f"✓ Loaded handlers from {handlers}")
        except ImportError as e:
            typer.echo(f"Error: Failed to load handlers module '{handlers}': {e}", err=True)
            typer.echo("   Make sure the module path is correct and accessible.", err=True)
            raise typer.Exit(1) from e

    # Initialize RuntimeLoop
    try:
        runtime = RuntimeLoop(
            config_path=config_path,
            optimized_du_path=optimized_du_path,
        )
    except Exception as e:
        typer.echo(f"Error: Failed to initialize runtime: {e}", err=True)
        raise typer.Exit(1) from e

    # Create and start CLI
    cli = SoniChatCLI(runtime, user_id=user_id)

    try:
        asyncio.run(cli.start())
    except KeyboardInterrupt:
        typer.echo("\n\n👋 Shutting down...")
    finally:
        # Cleanup runtime
        try:
            asyncio.run(runtime.cleanup())
        except Exception as e:
            typer.echo(f"Warning: Error during cleanup: {e}", err=True)
