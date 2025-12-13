# CLI Implementation: Milestone 1 - Basic Interactive Console

This document provides detailed implementation guidance for Milestone 1 of the CLI strategy.

## Overview

Implement a basic interactive console (`soni chat`) that allows users to test the Soni assistant in a simple read-eval-print loop (REPL).

## Requirements

### Functional Requirements

1. **Command**: `soni chat --config <path>`
   - Required: `--config` or `-c` option for YAML configuration file
   - Optional: `--user-id` or `-u` for custom user ID (default: auto-generated)

2. **Interactive Loop**:
   - Display welcome message
   - Prompt for user input: `You: `
   - Process message through RuntimeLoop
   - Display response: `Assistant: `
   - Continue until exit

3. **Exit Commands**:
   - `exit` - Exit gracefully
   - `quit` - Exit gracefully
   - `Ctrl+C` (KeyboardInterrupt) - Exit gracefully
   - `Ctrl+D` (EOF) - Exit gracefully

4. **Error Handling**:
   - Display clear error messages
   - Continue loop on non-fatal errors
   - Exit gracefully on fatal errors

### Non-Functional Requirements

- All text in English (per project rules)
- Async support (use `asyncio` for RuntimeLoop)
- Clean exit (no tracebacks on normal exit)
- Responsive (process messages quickly)

## Implementation Plan

### File Structure

```
src/soni/cli/
├── __init__.py
├── main.py          # Register chat command
├── chat.py          # NEW: Chat command implementation
├── optimize.py
└── server.py
```

### Implementation Steps

#### Step 1: Create `chat.py` Module

Create `src/soni/cli/chat.py` with:

```python
"""CLI command for interactive chat console"""

import asyncio
import logging
import uuid
from pathlib import Path

import typer

from soni.core.config import ConfigLoader
from soni.core.errors import ConfigurationError, SoniError
from soni.runtime.runtime import RuntimeLoop

logger = logging.getLogger(__name__)

app = typer.Typer(
    name="chat",
    help="Interactive chat console for testing Soni assistant",
    add_completion=False,
)


@app.command()
def start(
    config: str = typer.Option(
        ...,
        "--config",
        "-c",
        help="Path to Soni configuration YAML file",
    ),
    user_id: str = typer.Option(
        None,
        "--user-id",
        "-u",
        help="User ID for conversation (default: auto-generated)",
    ),
) -> None:
    """
    Start interactive chat console.

    This command starts an interactive session where you can chat with
    the Soni assistant. Type your messages and press Enter to send.
    Type 'exit' or 'quit' to end the session.

    Args:
        config: Path to configuration YAML file
        user_id: Optional user ID for conversation
    """
    # Validate config file
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

    # Generate user_id if not provided
    if user_id is None:
        user_id = f"cli-{uuid.uuid4().hex[:8]}"
        typer.echo(f"Using user ID: {user_id}")

    # Start interactive loop
    try:
        asyncio.run(_run_chat_loop(config_path, user_id))
    except KeyboardInterrupt:
        typer.echo("\n\n👋 Goodbye!")
    except Exception as e:
        typer.echo(f"\n❌ Unexpected error: {e}", err=True)
        raise typer.Exit(1) from e


async def _run_chat_loop(config_path: Path, user_id: str) -> None:
    """
    Run the interactive chat loop.

    Args:
        config_path: Path to configuration file
        user_id: User ID for conversation
    """
    # Initialize runtime
    typer.echo("\n🚀 Initializing Soni runtime...")
    try:
        runtime = RuntimeLoop(config_path=config_path)
        typer.echo("✓ Runtime initialized\n")
    except Exception as e:
        typer.echo(f"Error: Failed to initialize runtime: {e}", err=True)
        raise typer.Exit(1) from e

    # Display welcome message
    typer.echo("=" * 60)
    typer.echo("Welcome to Soni Interactive Console!")
    typer.echo("=" * 60)
    typer.echo("Type 'exit' or 'quit' to end the session.")
    typer.echo("Type 'help' for available commands.")
    typer.echo("")

    # Main loop
    while True:
        try:
            # Get user input
            user_input = input("You: ").strip()

            # Handle empty input
            if not user_input:
                continue

            # Handle exit commands
            if user_input.lower() in ("exit", "quit"):
                typer.echo("\n👋 Goodbye!")
                break

            # Handle help command
            if user_input.lower() == "help":
                _show_help()
                continue

            # Process message
            try:
                response = await runtime.process_message(
                    user_msg=user_input,
                    user_id=user_id,
                )
                typer.echo(f"Assistant: {response}\n")
            except SoniError as e:
                typer.echo(f"Error: {e}\n", err=True)
                # Continue loop on SoniError (non-fatal)
            except Exception as e:
                typer.echo(f"Unexpected error: {e}\n", err=True)
                logger.exception("Unexpected error in chat loop")
                # Continue loop on unexpected errors

        except EOFError:
            # Handle Ctrl+D
            typer.echo("\n\n👋 Goodbye!")
            break
        except KeyboardInterrupt:
            # Handle Ctrl+C
            typer.echo("\n\n👋 Goodbye!")
            break


def _show_help() -> None:
    """Display help message."""
    typer.echo("\nAvailable commands:")
    typer.echo("  exit, quit  - End the session")
    typer.echo("  help        - Show this help message")
    typer.echo("")
```

#### Step 2: Register Command in `main.py`

Update `src/soni/cli/main.py`:

```python
"""Main CLI entry point for Soni Framework"""

import typer

from soni.cli import chat as chat_module
from soni.cli import optimize as optimize_module
from soni.cli import server as server_module

app = typer.Typer(
    name="soni",
    help="Soni Framework - Open Source Conversational AI Framework",
    add_completion=False,
)

# Register subcommands
app.add_typer(chat_module.app, name="chat", help="Interactive chat console")
app.add_typer(optimize_module.app, name="optimize", help="Optimize NLU modules with DSPy")
app.add_typer(server_module.app, name="server", help="Start the Soni API server")

# ... rest of the file ...
```

#### Step 3: Add Tests

Create `tests/unit/test_cli_chat.py`:

```python
"""Tests for CLI chat command"""

import asyncio
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from typer.testing import CliRunner

from soni.cli.chat import app

runner = CliRunner()


def test_chat_command_help():
    """Test chat command help message"""
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "Interactive chat console" in result.stdout
    assert "--config" in result.stdout


def test_chat_command_missing_config():
    """Test chat command with missing config file"""
    result = runner.invoke(app, ["--config", "nonexistent.yaml"])
    assert result.exit_code == 1
    assert "not found" in result.stdout


def test_chat_command_invalid_config():
    """Test chat command with invalid config file"""
    # Create a temporary invalid YAML file
    invalid_config = Path("/tmp/invalid_soni_config.yaml")
    invalid_config.write_text("invalid: yaml: content: [")

    try:
        result = runner.invoke(app, ["--config", str(invalid_config)])
        assert result.exit_code == 1
        assert "Invalid configuration" in result.stdout
    finally:
        invalid_config.unlink(missing_ok=True)


@patch("soni.cli.chat.RuntimeLoop")
@patch("soni.cli.chat.input")
@patch("soni.cli.chat.typer.echo")
def test_chat_command_exit(mock_echo, mock_input, mock_runtime_class):
    """Test chat command exit behavior"""
    # Arrange
    mock_runtime = MagicMock()
    mock_runtime.process_message = AsyncMock(return_value="Hello!")
    mock_runtime_class.return_value = mock_runtime
    mock_input.side_effect = ["exit"]

    # Act
    result = runner.invoke(
        app,
        ["--config", "examples/flight_booking/soni.yaml"],
        input="exit\n",
    )

    # Assert
    assert result.exit_code == 0
    mock_echo.assert_any_call("👋 Goodbye!")


@patch("soni.cli.chat.RuntimeLoop")
@patch("soni.cli.chat.input")
@patch("soni.cli.chat.typer.echo")
def test_chat_command_conversation(mock_echo, mock_input, mock_runtime_class):
    """Test chat command conversation flow"""
    # Arrange
    mock_runtime = MagicMock()
    mock_runtime.process_message = AsyncMock(return_value="I can help you!")
    mock_runtime_class.return_value = mock_runtime
    mock_input.side_effect = ["Hello", "exit"]

    # Act
    with patch("asyncio.run") as mock_asyncio_run:
        # Mock the async function
        async def mock_run_loop(*args, **kwargs):
            # Simulate the loop
            await mock_runtime.process_message("Hello", "test-user")
            mock_echo("Assistant: I can help you!\n")
            mock_echo("👋 Goodbye!")

        mock_asyncio_run.side_effect = mock_run_loop
        result = runner.invoke(
            app,
            ["--config", "examples/flight_booking/soni.yaml"],
        )

    # Assert
    assert result.exit_code == 0
```

## Testing Strategy

### Unit Tests
- Test command registration
- Test config validation
- Test user_id generation
- Test exit commands
- Test help command
- Test error handling

### Integration Tests
- Test full conversation flow
- Test with real configuration file
- Test error recovery
- Test graceful exit

### Manual Testing
1. Start chat: `soni chat -c examples/flight_booking/soni.yaml`
2. Send messages and verify responses
3. Test exit commands
4. Test error handling
5. Test with custom user_id

## Acceptance Criteria Checklist

- [ ] Command `soni chat --config <path>` works
- [ ] Config file validation works
- [ ] Auto-generated user_id works
- [ ] Custom user_id with `--user-id` works
- [ ] Interactive loop works (input/output)
- [ ] Exit with `exit` command works
- [ ] Exit with `quit` command works
- [ ] Exit with `Ctrl+C` works
- [ ] Exit with `Ctrl+D` works
- [ ] Error messages are clear
- [ ] Non-fatal errors don't break the loop
- [ ] Welcome message displays correctly
- [ ] Help command works
- [ ] All tests pass
- [ ] Code follows project style (ruff, mypy)
- [ ] Documentation updated

## Dependencies

- **Existing**: `typer`, `asyncio`, `RuntimeLoop`
- **No new dependencies required**

## Notes

- Use `asyncio.run()` to run the async chat loop
- Handle `KeyboardInterrupt` and `EOFError` for clean exit
- Use `input()` for synchronous input (Python's `input()` is blocking but works fine for CLI)
- Consider using `rich` library in future milestones for better formatting
- All user-facing text must be in English

## Future Enhancements (Not in Milestone 1)

- Streaming mode (`--stream`)
- Verbose mode (`--verbose`)
- Color output
- Better formatting
- Command history
- Auto-completion
