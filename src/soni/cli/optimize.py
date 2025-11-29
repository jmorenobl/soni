"""CLI command for optimizing SoniDU modules"""

import json
from pathlib import Path

import dspy
import typer
from typer import Option

from soni.du.optimizers import load_optimized_module, optimize_soni_du

app = typer.Typer(help="Optimize SoniDU modules with DSPy")


def _load_trainset_from_file(trainset_path: Path) -> list[dspy.Example]:
    """
    Load trainset from a JSON file.

    Expected format:
    [
        {
            "user_message": "...",
            "dialogue_history": "...",
            "current_slots": "{}",
            "available_actions": "[]",
            "current_flow": "none",
            "structured_command": "...",
            "extracted_slots": "{}",
            "confidence": "0.85",
            "reasoning": "..."
        },
        ...
    ]

    Args:
        trainset_path: Path to JSON file with training examples

    Returns:
        List of dspy.Example instances

    Raises:
        FileNotFoundError: If file doesn't exist
        ValueError: If file format is invalid
    """
    if not trainset_path.exists():
        raise FileNotFoundError(f"Trainset file not found: {trainset_path}")

    with open(trainset_path, encoding="utf-8") as f:
        data = json.load(f)

    if not isinstance(data, list):
        raise ValueError("Trainset file must contain a JSON array")

    examples = []
    for item in data:
        example = dspy.Example(**item).with_inputs(
            "user_message",
            "dialogue_history",
            "current_slots",
            "available_actions",
            "current_flow",
        )
        examples.append(example)

    return examples


@app.command()
def optimize(
    trainset_path: Path = Option(
        ...,
        "--trainset",
        "-t",
        help="Path to JSON file with training examples",
    ),
    optimizer: str = Option(
        "MIPROv2",
        "--optimizer",
        "-o",
        help="Optimizer type (currently only MIPROv2)",
    ),
    num_trials: int = Option(
        10,
        "--trials",
        "-n",
        help="Number of optimization trials",
    ),
    timeout: int = Option(
        600,
        "--timeout",
        help="Maximum optimization time in seconds",
    ),
    output_dir: Path = Option(
        None,
        "--output",
        "-O",
        help="Directory to save optimized module (optional)",
    ),
) -> None:
    """
    Optimize a SoniDU module using DSPy optimizers.

    Example:
        soni optimize --trainset data/trainset.json --trials 10 --output models/
    """
    typer.echo(f"Loading trainset from: {trainset_path}")
    try:
        trainset = _load_trainset_from_file(trainset_path)
    except Exception as e:
        typer.echo(f"Error loading trainset: {e}", err=True)
        raise typer.Exit(1)

    typer.echo(f"Loaded {len(trainset)} training examples")
    typer.echo(f"Using optimizer: {optimizer}")
    typer.echo(f"Number of trials: {num_trials}")
    typer.echo(f"Timeout: {timeout}s")
    typer.echo("")

    try:
        optimized_module, metrics = optimize_soni_du(
            trainset=trainset,
            optimizer_type=optimizer,
            num_trials=num_trials,
            timeout_seconds=timeout,
            output_dir=output_dir,
        )
    except Exception as e:
        typer.echo(f"Optimization failed: {e}", err=True)
        raise typer.Exit(1)

    # Print summary
    typer.echo("")
    typer.echo("=" * 60)
    typer.echo("Optimization Summary")
    typer.echo("=" * 60)
    typer.echo(f"Baseline accuracy: {metrics['baseline_accuracy']:.2%}")
    typer.echo(f"Optimized accuracy: {metrics['optimized_accuracy']:.2%}")
    typer.echo(f"Improvement: {metrics['improvement_pct']:+.1f}%")
    typer.echo(f"Total time: {metrics['total_time']:.1f}s")
    typer.echo("")

    if output_dir:
        typer.echo(f"Optimized module saved to: {output_dir}/optimized_nlu.json")


@app.command()
def load(
    module_path: Path = Option(
        ...,
        "--module",
        "-m",
        help="Path to saved optimized module JSON file",
    ),
) -> None:
    """
    Load and validate a previously optimized module.

    Example:
        soni optimize load --module models/optimized_nlu.json
    """
    typer.echo(f"Loading module from: {module_path}")
    try:
        module = load_optimized_module(module_path)
        typer.echo("✅ Module loaded successfully")
        typer.echo(f"Module type: {type(module).__name__}")
    except Exception as e:
        typer.echo(f"Error loading module: {e}", err=True)
        raise typer.Exit(1)
