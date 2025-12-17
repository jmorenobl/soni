"""
Flow Testing CLI Runner.

Run complex banking flow scenarios with configurable verbosity.

Usage:
    python -m examples.banking.scripts.runner --scenario check_balance_happy -v
    python -m examples.banking.scripts.runner --scenario transfer_basic -vvv
    python -m examples.banking.scripts.runner --scenario all -vv
    python -m examples.banking.scripts.runner --list
    python -m examples.banking.scripts.runner --tag complex -vvv
"""

from __future__ import annotations

import asyncio
from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

from examples.banking.scripts.base import FlowTestRunner, LogLevel, Scenario

# Import all scenarios
from examples.banking.scripts.scenarios import (
    account,
    bills,
    cards,
    complex,
    confirmation,
    initialization,
    security,
    transfer,
)

app = typer.Typer(
    name="flow-runner",
    help="Run banking flow scenarios with detailed logging",
    add_completion=False,
)

console = Console()


def _collect_all_scenarios() -> dict[str, Scenario]:
    """Collect all scenarios from all modules."""
    all_scenarios: dict[str, Scenario] = {
        **{s.name: s for s in account.SCENARIOS},
        **{s.name: s for s in transfer.SCENARIOS},
        **{s.name: s for s in cards.SCENARIOS},
        **{s.name: s for s in bills.SCENARIOS},
        **{s.name: s for s in complex.SCENARIOS},
        **{s.name: s for s in confirmation.SCENARIOS},
        **{s.name: s for s in initialization.SCENARIOS},
        **{s.name: s for s in security.SCENARIOS},
    }
    return all_scenarios


def _get_config_path() -> Path:
    """Get the banking example config path."""
    # Assuming we're running from project root
    candidates = [
        Path("examples/banking/domain"),
        Path(__file__).parent.parent / "domain",
    ]

    for candidate in candidates:
        if candidate.exists():
            return candidate

    raise FileNotFoundError("Could not find banking domain config")


@app.command("list")
def list_scenarios(
    tag: str | None = typer.Option(None, "--tag", "-t", help="Filter by tag"),
) -> None:
    """List all available scenarios."""
    scenarios = _collect_all_scenarios()

    table = Table(title="Available Scenarios", show_header=True)
    table.add_column("Name", style="cyan")
    table.add_column("Description")
    table.add_column("Turns", justify="right")
    table.add_column("Tags", style="dim")

    for name, scenario in sorted(scenarios.items()):
        if tag and tag not in scenario.tags:
            continue

        table.add_row(
            name,
            scenario.description,
            str(len(scenario.turns)),
            ", ".join(scenario.tags),
        )

    console.print(table)
    console.print(f"\nTotal: {len(scenarios)} scenarios")


@app.command("run")
def run_scenario(
    scenario: str = typer.Argument(
        ...,
        help="Scenario name or 'all' to run all scenarios",
    ),
    verbose: int = typer.Option(
        1,
        "--verbose",
        "-v",
        count=True,
        help="Verbosity level: -v (basic), -vv (detailed), -vvv (debug)",
    ),
    tag: str | None = typer.Option(
        None,
        "--tag",
        "-t",
        help="Run scenarios with this tag (only with 'all')",
    ),
    real_nlu: bool = typer.Option(
        False,
        "--real-nlu",
        help="Use real LLM for NLU instead of mocks",
    ),
) -> None:
    """Run a scenario or all scenarios."""
    # Map verbosity count to LogLevel
    level = LogLevel(min(verbose, 3))

    scenarios = _collect_all_scenarios()

    # Determine which scenarios to run
    if scenario.lower() == "all":
        to_run = list(scenarios.values())
        if tag:
            to_run = [s for s in to_run if tag in s.tags]
    else:
        if scenario not in scenarios:
            console.print(f"[red]Scenario not found: {scenario}[/]")
            console.print("Use --list to see available scenarios")
            raise typer.Exit(1)
        to_run = [scenarios[scenario]]

    if not to_run:
        console.print("[yellow]No scenarios to run[/]")
        raise typer.Exit(0)

    console.print(f"[bold]Running {len(to_run)} scenario(s) at verbosity level {level.name}[/]")

    if real_nlu:
        console.print("[yellow]Using real NLU (LLM calls)[/]")
    else:
        console.print("[dim]Using mock NLU (deterministic)[/]")

    # Get config path
    try:
        config_path = _get_config_path()
    except FileNotFoundError as e:
        console.print(f"[red]Config error: {e}[/]")
        raise typer.Exit(1) from None

    # Run scenarios
    async def _run() -> list[bool]:
        runner = FlowTestRunner(
            config_path=config_path,
            level=level,
            use_real_nlu=real_nlu,
        )
        await runner.initialize()

        results = await runner.run_all(to_run)
        return [r.passed for r in results]

    results = asyncio.run(_run())

    # Exit with appropriate code
    if all(results):
        raise typer.Exit(0)
    else:
        raise typer.Exit(1)


@app.callback(invoke_without_command=True)
def main(
    ctx: typer.Context,
    version: bool = typer.Option(False, "--version", help="Show version"),
) -> None:
    """Banking Flow Test Runner - Debug complex conversational flows."""
    if version:
        console.print("flow-runner v1.0.0")
        raise typer.Exit(0)

    if ctx.invoked_subcommand is None:
        console.print("Use --help to see available commands")
        raise typer.Exit(0)


if __name__ == "__main__":
    app()
