## Task: TD-010 - Refactor run_chat into ChatRunner Class

**ID de tarea:** TD-010
**Fase:** Phase 4 - CLI
**Prioridad:** 🔴 HIGH
**Dependencias:** Ninguna
**Duración estimada:** 2 horas

### Objetivo

Refactorizar la función `run_chat` de 73 statements (complejidad 16) en una clase `ChatRunner` bien estructurada que siga los principios SOLID.

### Contexto

Ruff reporta problemas significativos con la función actual:

```
C901 `run_chat` is too complex (16 > 10)
PLR0913 Too many arguments in function definition (6 > 5)
PLR0915 Too many statements (73 > 50)
```

**Impacto:** Difícil de mantener, testear y extender.

**Archivo afectado:** [cli/commands/chat.py](file:///Users/jorge/Projects/Playground/soni/src/soni/cli/commands/chat.py)

### Entregables

- [ ] Crear clase `ChatRunner` con responsabilidades bien definidas
- [ ] Extraer métodos: `setup()`, `run_loop()`, `handle_input()`, `cleanup()`
- [ ] Reducir complejidad ciclomática a < 10
- [ ] Mantener la misma interfaz CLI
- [ ] Añadir tests para la nueva clase

### Implementación Detallada

#### Paso 1: Crear la clase ChatRunner

**Archivo a crear:** `src/soni/cli/chat_runner.py`

```python
"""Interactive chat runner for Soni CLI."""

import asyncio
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from soni.config.loader import load_config
from soni.runtime.loop import RuntimeLoop


@dataclass
class ChatConfig:
    """Configuration for chat runner."""

    config_path: Path
    module: str | None = None
    thread_id: str | None = None
    model: str | None = None
    verbose: bool = False
    debug: bool = False


class ChatRunner:
    """Interactive chat session runner.

    Encapsulates the setup, execution, and cleanup of an
    interactive chat session with the Soni runtime.

    Follows SRP: Only responsible for running chat sessions.
    """

    def __init__(self, config: ChatConfig) -> None:
        """Initialize chat runner.

        Args:
            config: Chat configuration
        """
        self._config = config
        self._runtime: RuntimeLoop | None = None
        self._thread_id: str | None = None
        self._running = False

    async def setup(self) -> None:
        """Initialize runtime and prepare for chat.

        Raises:
            ConfigurationError: If config is invalid
        """
        # Load domain configuration
        domain_config = load_config(self._config.config_path)

        # Import handler module if specified
        handlers = self._load_handlers()

        # Initialize runtime
        self._runtime = await RuntimeLoop.create(
            config=domain_config,
            handlers=handlers,
            model=self._config.model,
        )

        # Setup thread
        self._thread_id = self._config.thread_id or self._generate_thread_id()

        if self._config.verbose:
            self._print_startup_info()

    def _load_handlers(self) -> dict[str, Any] | None:
        """Load handler module if specified."""
        if not self._config.module:
            return None

        import importlib
        module = importlib.import_module(self._config.module)
        return getattr(module, "handlers", None)

    def _generate_thread_id(self) -> str:
        """Generate a new thread ID."""
        import uuid
        return str(uuid.uuid4())

    def _print_startup_info(self) -> None:
        """Print startup information."""
        from rich.console import Console
        console = Console()
        console.print(f"[bold green]Soni Chat[/]")
        console.print(f"Config: {self._config.config_path}")
        console.print(f"Thread: {self._thread_id}")
        console.print("Type 'quit' or 'exit' to end the session.")
        console.print("-" * 40)

    async def run_loop(self) -> None:
        """Run the main chat loop.

        Continuously prompts for user input and processes messages
        until exit command is received.
        """
        from rich.console import Console
        from rich.prompt import Prompt

        console = Console()
        self._running = True

        while self._running:
            try:
                user_input = Prompt.ask("[bold blue]You[/]")

                if self._is_exit_command(user_input):
                    console.print("[yellow]Goodbye![/]")
                    break

                response = await self.handle_input(user_input)
                console.print(f"[bold green]Assistant[/]: {response}")

            except KeyboardInterrupt:
                console.print("\n[yellow]Session interrupted.[/]")
                break
            except Exception as e:
                if self._config.debug:
                    console.print_exception()
                else:
                    console.print(f"[red]Error: {e}[/]")

    def _is_exit_command(self, user_input: str) -> bool:
        """Check if input is an exit command."""
        return user_input.strip().lower() in ("quit", "exit", "q", "/quit", "/exit")

    async def handle_input(self, user_input: str) -> str:
        """Process user input and return response.

        Args:
            user_input: User's message

        Returns:
            Assistant's response

        Raises:
            RuntimeError: If runtime not initialized
        """
        if self._runtime is None:
            raise RuntimeError("Chat runner not initialized. Call setup() first.")

        result = await self._runtime.process_message(
            message=user_input,
            thread_id=self._thread_id,
        )

        return result.response

    async def cleanup(self) -> None:
        """Clean up resources."""
        self._running = False
        if self._runtime is not None:
            await self._runtime.cleanup()
            self._runtime = None

    async def __aenter__(self) -> "ChatRunner":
        """Async context manager entry."""
        await self.setup()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Async context manager exit."""
        await self.cleanup()


async def run_chat_session(config: ChatConfig) -> None:
    """Run an interactive chat session.

    Convenience function that handles setup and cleanup.

    Args:
        config: Chat configuration
    """
    async with ChatRunner(config) as runner:
        await runner.run_loop()
```

#### Paso 2: Actualizar cli/commands/chat.py

**Archivo a modificar:** `src/soni/cli/commands/chat.py`

```python
"""Chat command for Soni CLI."""

import asyncio
from pathlib import Path
from typing import Annotated, Optional

import typer

from soni.cli.chat_runner import ChatConfig, run_chat_session


def run_chat(
    config_path: Annotated[
        Path,
        typer.Argument(help="Path to domain configuration directory"),
    ],
    module: Annotated[
        Optional[str],
        typer.Option("--module", "-m", help="Handler module to import"),
    ] = None,
    thread_id: Annotated[
        Optional[str],
        typer.Option("--thread", "-t", help="Thread ID for conversation"),
    ] = None,
    model: Annotated[
        Optional[str],
        typer.Option("--model", help="LLM model to use"),
    ] = None,
    verbose: Annotated[
        bool,
        typer.Option("--verbose", "-v", help="Verbose output"),
    ] = False,
    debug: Annotated[
        bool,
        typer.Option("--debug", help="Debug mode"),
    ] = False,
) -> None:
    """Start an interactive chat session."""
    config = ChatConfig(
        config_path=config_path,
        module=module,
        thread_id=thread_id,
        model=model,
        verbose=verbose,
        debug=debug,
    )

    asyncio.run(run_chat_session(config))
```

### TDD Cycle

#### Red Phase: Write Failing Tests

**Test file:** `tests/unit/cli/test_chat_runner.py`

```python
"""Tests for ChatRunner class."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from soni.cli.chat_runner import ChatRunner, ChatConfig


class TestChatRunner:
    """Tests for ChatRunner."""

    @pytest.fixture
    def config(self, tmp_path):
        """Create test config."""
        return ChatConfig(
            config_path=tmp_path,
            verbose=False,
            debug=False,
        )

    def test_init_stores_config(self, config):
        """Test that config is stored correctly."""
        runner = ChatRunner(config)
        assert runner._config == config
        assert runner._runtime is None

    @pytest.mark.asyncio
    async def test_setup_initializes_runtime(self, config):
        """Test that setup initializes runtime."""
        with patch("soni.cli.chat_runner.load_config") as mock_load:
            with patch("soni.cli.chat_runner.RuntimeLoop") as mock_runtime:
                mock_runtime.create = AsyncMock()
                runner = ChatRunner(config)
                await runner.setup()
                assert runner._runtime is not None

    @pytest.mark.asyncio
    async def test_cleanup_releases_resources(self, config):
        """Test that cleanup releases resources."""
        runner = ChatRunner(config)
        runner._runtime = AsyncMock()
        await runner.cleanup()
        assert runner._runtime is None
        runner._runtime = None  # Reset for assertion

    def test_is_exit_command_recognizes_quit(self, config):
        """Test exit command recognition."""
        runner = ChatRunner(config)
        assert runner._is_exit_command("quit")
        assert runner._is_exit_command("exit")
        assert runner._is_exit_command("q")
        assert runner._is_exit_command("/quit")
        assert not runner._is_exit_command("hello")

    @pytest.mark.asyncio
    async def test_handle_input_raises_if_not_setup(self, config):
        """Test error when handling input without setup."""
        runner = ChatRunner(config)
        with pytest.raises(RuntimeError, match="not initialized"):
            await runner.handle_input("hello")

    @pytest.mark.asyncio
    async def test_context_manager_calls_setup_and_cleanup(self, config):
        """Test async context manager protocol."""
        with patch.object(ChatRunner, "setup", new_callable=AsyncMock) as mock_setup:
            with patch.object(ChatRunner, "cleanup", new_callable=AsyncMock) as mock_cleanup:
                async with ChatRunner(config):
                    pass
                mock_setup.assert_called_once()
                mock_cleanup.assert_called_once()
```

**Verify tests fail:**
```bash
uv run pytest tests/unit/cli/test_chat_runner.py -v
# Expected: FAILED (module doesn't exist yet)
```

#### Green Phase: Make Tests Pass

Implement the ChatRunner class as described.

```bash
uv run pytest tests/unit/cli/test_chat_runner.py -v
# Expected: PASSED ✅
```

### Criterios de Éxito

- [ ] `run_chat` function reduced to < 20 lines
- [ ] `ChatRunner` class with clear SRP
- [ ] Cyclomatic complexity < 10 for all methods
- [ ] All existing CLI functionality preserved
- [ ] New unit tests for ChatRunner
- [ ] `uv run ruff check src/soni/cli/` passes without C901, PLR0913, PLR0915

### Validación Manual

**Comandos para validar:**

```bash
# Verify ruff passes
uv run ruff check src/soni/cli/commands/chat.py

# Verify complexity
uv run ruff check src/soni/cli/ --select C901,PLR0913,PLR0915

# Test CLI works
uv run soni chat --help
uv run soni chat examples/banking/domain --verbose

# Run tests
uv run pytest tests/unit/cli/ -v

# Type check
uv run mypy src/soni/cli/
```

**Resultado esperado:**
- No complexity warnings from ruff
- CLI works as before
- All tests pass

### Referencias

- [Technical Debt Analysis](file:///Users/jorge/Projects/Playground/soni/workflow/analysis/technical-debt-analysis.md#L96-120)
- [Extract Class Refactoring](https://refactoring.com/catalog/extractClass.html)
- [SRP - Single Responsibility Principle](https://en.wikipedia.org/wiki/Single-responsibility_principle)

### Notas Adicionales

- `ChatRunner` puede ser reutilizado para tests de integración
- El async context manager permite uso limpio con `async with`
- Considerar añadir evento hooks para extensibilidad futura
- La clase facilita mocking para tests
