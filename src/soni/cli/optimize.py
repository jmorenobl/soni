"""CLI command for optimizing SoniDU modules."""

import json
from pathlib import Path

import dspy
import typer
from typer import Option

from soni.core.config import SoniConfig
from soni.dataset.conversation_simulator import ConversationSimulator
from soni.du.optimizers import load_optimized_module, optimize_soni_du

app = typer.Typer(help="Optimize SoniDU modules with DSPy")


def _load_trainset_from_file(trainset_path: Path) -> list[dspy.Example]:
    """Load trainset from a JSON file.

    Expected format:
    [
        {
            "user_message": "...",
            "dialogue_history": "...",
            ...
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
    config_path: Path = Option(
        ...,
        "--config",
        "-c",
        help="Path to soni.yaml configuration file",
    ),
    trainset_path: Path | None = Option(
        None,
        "--trainset",
        "-t",
        help="Optional: Override with custom JSON trainset",
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
    examples_per_pattern: int = Option(
        3,
        "--examples",
        "-e",
        help="Number of example variations per pattern when generating from YAML",
    ),
) -> None:
    """Optimize a SoniDU module for a specific domain.

    This command generates training examples from your soni.yaml configuration
    by simulating conversations based on your flow definitions, then optimizes
    the NLU module for your specific domain.

    Example:
        soni optimize --config examples/banking/soni.yaml --output models/
    """
    # Load config
    typer.echo(f"Loading configuration from: {config_path}")
    try:
        config = SoniConfig.from_yaml(config_path)
    except Exception as e:
        typer.echo(f"Error loading configuration: {e}", err=True)
        raise typer.Exit(1)

    typer.echo(f"  Found {len(config.flows)} flows")
    typer.echo(f"  Found {len(config.slots)} slots")
    typer.echo(f"  Found {len(config.actions)} actions")
    typer.echo("")

    # Configure DSPy LM from YAML settings
    import dspy

    nlu_config = config.settings.models.nlu
    model_name = f"{nlu_config.provider}/{nlu_config.model}"
    typer.echo(f"Configuring LM: {model_name}")
    lm = dspy.LM(model_name, temperature=nlu_config.temperature, max_tokens=1024)
    dspy.configure(lm=lm)

    # Generate or load trainset
    if trainset_path:
        typer.echo(f"Loading custom trainset from: {trainset_path}")
        try:
            trainset = _load_trainset_from_file(trainset_path)
        except (FileNotFoundError, OSError, ValueError, json.JSONDecodeError) as e:
            typer.echo(f"Error loading trainset: {e}", err=True)
            raise typer.Exit(1)
    else:
        typer.echo("Generating trainset from YAML configuration...")
        try:
            simulator = ConversationSimulator(config)
            trainset = simulator.generate_dataset(
                examples_per_pattern=examples_per_pattern,
                include_edge_cases=True,
            )
        except Exception as e:
            typer.echo(f"Error generating trainset: {e}", err=True)
            raise typer.Exit(1)

    typer.echo(f"Generated {len(trainset)} training examples")
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
    except (RuntimeError, ValueError, TypeError) as e:
        typer.echo(f"Optimization failed: {e}", err=True)
        raise typer.Exit(1)
    except Exception as e:
        typer.echo(f"Unexpected error during optimization: {e}", err=True)
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
    """Load and validate a previously optimized module.

    Example:
        soni optimize load --module models/optimized_nlu.json
    """
    typer.echo(f"Loading module from: {module_path}")
    try:
        module = load_optimized_module(module_path)
        typer.echo("✅ Module loaded successfully")
        typer.echo(f"Module type: {type(module).__name__}")
    except (FileNotFoundError, OSError, RuntimeError, ValueError) as e:
        typer.echo(f"Error loading module: {e}", err=True)
        raise typer.Exit(1)
    except Exception as e:
        typer.echo(f"Unexpected error loading module: {e}", err=True)
        raise typer.Exit(1)


@app.command()
def preview(
    config_path: Path = Option(
        ...,
        "--config",
        "-c",
        help="Path to soni.yaml configuration file",
    ),
    examples_per_pattern: int = Option(
        3,
        "--examples",
        "-e",
        help="Number of example variations per pattern",
    ),
    output_file: Path | None = Option(
        None,
        "--output",
        "-o",
        help="Optional: Save generated examples to JSON file",
    ),
) -> None:
    """Preview generated training examples without running optimization.

    Useful for inspecting and validating the generated dataset before
    running a full optimization.

    Example:
        soni optimize preview --config examples/banking/soni.yaml
    """
    typer.echo(f"Loading configuration from: {config_path}")
    try:
        config = SoniConfig.from_yaml(config_path)
    except Exception as e:
        typer.echo(f"Error loading configuration: {e}", err=True)
        raise typer.Exit(1)

    typer.echo("Generating training examples...")
    simulator = ConversationSimulator(config)
    trainset = simulator.generate_dataset(
        examples_per_pattern=examples_per_pattern,
        include_edge_cases=True,
    )

    typer.echo(f"\nGenerated {len(trainset)} examples:")
    typer.echo("-" * 50)

    # Show sample examples
    for i, example in enumerate(trainset[:10]):
        typer.echo(f"\n[Example {i + 1}]")
        typer.echo(f"  User: {example.user_message}")
        result = example.result
        typer.echo(f"  Expected: {result.message_type.value} → {result.command}")
        if result.slots:
            slots_str = ", ".join(f"{s.name}={s.value}" for s in result.slots)
            typer.echo(f"  Slots: {slots_str}")

    if len(trainset) > 10:
        typer.echo(f"\n... and {len(trainset) - 10} more examples")

    if output_file:
        # Save to JSON for inspection
        import json

        examples_data = []
        for ex in trainset:
            examples_data.append(
                {
                    "user_message": ex.user_message,
                    "expected_type": ex.result.message_type.value,
                    "expected_command": ex.result.command,
                    "slots": [{"name": s.name, "value": s.value} for s in ex.result.slots],
                }
            )
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(examples_data, f, indent=2)
        typer.echo(f"\nSaved to: {output_file}")
