"""Optimization command."""

import json
from pathlib import Path

import dspy
import typer
from rich.console import Console
from rich.table import Table

from soni.core.commands import Command
from soni.dataset import DatasetBuilder
from soni.du.optimizer import create_metric, optimize_du

app = typer.Typer(help="Optimize NLU module")
console = Console()


def _get_metric():
    # Helper to create metric
    def validate_command(expected: Command, actual: Command) -> bool:
        # Simple type check for now
        # Ideally we check fields too
        return type(expected) is type(actual)

    return create_metric(validate_command)


@app.command()
def run(
    config: Path = typer.Option(..., "--config", "-c", help="Path to soni.yaml", exists=True),
    dataset: Path | None = typer.Option(None, "--trainset", "-t", help="Generated dataset path"),
    output: Path = typer.Option(Path("models"), "--output", "-o", help="Output directory"),
    trials: int = typer.Option(10, "--trials", "-n", help="Optimization trials"),
    include_slots: bool = typer.Option(
        False, "--include-slots", help="Optimize slot extraction too"
    ),
):
    """Run optimization pipeline."""

    # 1. Load Config
    # 1. Load Config
    from soni.config.loader import ConfigLoader

    soni_config = ConfigLoader.load(config)

    # 2. Config DSPy using centralized bootstrapper
    from soni.core.dspy_service import DSPyBootstrapper

    try:
        bootstrapper = DSPyBootstrapper(soni_config)
        bootstrapper.configure()
    except Exception as e:
        console.print(f"[red]DSPy init failed: {e}[/]")
        raise typer.Exit(1)

    # 3. Get/Generate Dataset
    if dataset:
        console.print(f"Loading dataset from {dataset}...")
        with open(dataset) as f:
            data = json.load(f)
            # Reconstruct dspy.Examples
            examples = []
            for item in data:
                # Assumption: dataset file matches expected format from scripts
                # We might need explicit deserialization logic if complex
                # For simplicity, using dspy.Example directly if structure matches
                examples.append(
                    dspy.Example(**item).with_inputs("user_message", "history", "context")
                )
    else:
        console.print("Generating training dataset...")
        builder = DatasetBuilder()
        examples = builder.build_all(examples_per_combination=3, include_edge_cases=True)
        console.print(f"Generated {len(examples)} examples.")

    # 4. Optimize
    console.print(f"Starting optimization (trials={trials})...")

    output.mkdir(parents=True, exist_ok=True)

    try:
        optimized = optimize_du(trainset=examples, metric=_get_metric(), auto="light")

        save_path = output / "optimized_nlu.json"
        optimized.save(str(save_path))

        console.print(f"[green]SoniDU Optimization complete![/] Saved to {save_path}")

    except Exception as e:
        console.print(f"[red]SoniDU Optimization failed: {e}[/]")
        # Do not raise immediately if we want to try slots
        if not include_slots:
            raise typer.Exit(1)

    # 5. Optimize Slots
    if include_slots:
        try:
            console.print("Starting SlotExtractor optimization...")
            from soni.dataset.domains import ALL_DOMAINS
            from soni.dataset.slot_extraction import SlotExtractionDatasetBuilder
            from soni.du.metrics import create_slot_extraction_metric
            from soni.du.optimizer import optimize_slot_extractor

            # Use ALL_DOMAINS for comprehensive training
            # This leverages the slot_extraction_cases defined in each domain
            slot_builder = SlotExtractionDatasetBuilder()
            all_slot_examples = []

            for domain_name, domain_config in ALL_DOMAINS.items():
                templates = slot_builder.build(domain_config)
                examples = [t.to_dspy_example() for t in templates]
                all_slot_examples.extend(examples)
                console.print(f"  [dim]{domain_name}: {len(examples)} examples[/]")

            console.print(f"Generated {len(all_slot_examples)} total slot examples.")

            if not all_slot_examples:
                console.print("[yellow]No slot examples generated. Skipping.[/]")
            else:
                optimized_slots = optimize_slot_extractor(
                    trainset=all_slot_examples, metric=create_slot_extraction_metric(), auto="light"
                )

                slot_save_path = output / "optimized_slot_extractor.json"
                optimized_slots.save(str(slot_save_path))

                console.print(
                    f"[green]SlotExtractor Optimization complete![/] Saved to {slot_save_path}"
                )

        except Exception as e:
            console.print(f"[red]SlotExtractor Optimization failed: {e}[/]")
            raise typer.Exit(1)


@app.command()
def preview(
    config: Path | None = typer.Option(
        None, "--config", "-c", help="Config file (currently unused)"
    ),
):
    """Preview generated examples."""
    builder = DatasetBuilder()
    examples = builder.build_all(examples_per_combination=1, include_edge_cases=False)

    table = Table(title="Generated Examples Preview")
    table.add_column("User Input")
    table.add_column("Expected Commands")

    for ex in examples[:10]:
        cmds = (
            ", ".join([type(c).__name__ for c in ex.result.commands])
            if hasattr(ex.result, "commands")
            else "None"
        )
        table.add_row(ex.user_message[:50], cmds)

    console.print(table)
    console.print(f"\n[dim]Total examples available: {len(examples)}[/]")
